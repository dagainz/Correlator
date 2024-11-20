import argparse
import asyncio
import pickle

from rstream import (
    AMQPMessage,
    Consumer,
    ConsumerOffsetSpecification,
    OffsetType,
    MessageContext,
    amqp_decoder,
)

from Correlator.config_store import RuntimeConfig
from Correlator.runtime_config import ApplicationConfig
from Correlator.core import Instance
from Correlator.reactor import ReactorConfig
from cli import BaseCLI


class EventToolCLI(BaseCLI):
    """ Basic CLI to list and report on events on the event stream

    In list mode, lists key information from events on the event stream within an offset range
    In inspect mode, it reports details of a single event, indexed by stream offset.
    In watch mode, it sits on the end of the event stream and reports on new events received

    """

    def __init__(self):

        parser = argparse.ArgumentParser(description='EventTool Utility')
        parser.add_argument('--id', required=True, help='Reactor ID')
        self._handle_configfile_argument(parser)
        parser.add_argument('-d', '--debug', action='store_true',
                            help='Enable more verbose output')
        parser.add_argument('-p', '--page', type=int, default=20,
                            help='How many events to display before a new header line is printed')
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('-l', '--list', type=self._offset_spec,
                           help='List events in stream according to this offset specification: Integer or range separated by hyphen.')
        group.add_argument('-i', '--inspect', type=int,
                           help='Inspect a single event in stream by its Integer offset.')
        group.add_argument('-w', '--watch', action='store_true',
                           help='Watch from the end of the event queue for new events')

        args = parser.parse_args()

        reactor_id = args.id
        configuration_prefix = f"reactors.{reactor_id}"

        if args.list:
            (self.test_start, self.test_end) = args.list
        else:
            self.inspect_mode = True
            self.test_start = args.inspect
            self.test_end = args.inspect

        print(
            f"Correlator {Instance.Version} EventTool utility. Using configuration from Reactor {reactor_id}\n")

        if not ApplicationConfig.load(args.config_file):
            raise ValueError('Error loading configuration file')

        config_block = ApplicationConfig.reactor_by_id(reactor_id)

        if not config_block:
            raise ValueError(
                f'Invalid Reactor ID: {reactor_id} found in configuration')

        # configuration_prefix = f"reactors.{reactor_id}"

        RuntimeConfig.add(ReactorConfig, configuration_prefix)

        ApplicationConfig.process_reactor_config(reactor_id)

        self.rmq_host = RuntimeConfig.get(
            f'{configuration_prefix}.rabbitmq_host')
        self.rmq_user = RuntimeConfig.get(
            f'{configuration_prefix}.rabbitmq_user')

        # Need to replace with hook into keyring here

        self.rmq_password = RuntimeConfig.get(
            f'{configuration_prefix}.rabbitmq_password')
        self.rmq_port = 5552
        self.rmq_event_stream = RuntimeConfig.get(
            f'{configuration_prefix}.rabbitmq_event_stream')

        # No need for reactor engine

        # RuntimeConfig.dump_to_log()

        self.total_messages = 0

        # Subscribe to event stream

        def output_header():
            print("Offset   Tenant          Event ID                 Summary\n"
                  "---------------------------------------------------------------------")

        async def consume():
            consumer = Consumer(
                host=self.rmq_host,
                port=self.rmq_port,
                vhost="/",
                username=self.rmq_user,
                password=self.rmq_password,
            )

            async def on_event(msg: AMQPMessage,
                               message_context: MessageContext):
                this_consumer = message_context.consumer
                offset = message_context.offset
                stream = this_consumer.get_stream(
                    message_context.subscriber_name)

                record = pickle.loads(msg.body)
                event = pickle.loads(record.obj)
                tenant_id = record.tenant_id

                if args.watch or args.list:
                    if self.total_messages != 0 and args.page != 0 and self.total_messages % args.page == 0:
                        output_header()
                    print(f"{offset:<8} {tenant_id:<16}{event.id:<25}{event}")
                else:
                    print(
                        f"-----------Event Information-----------\n\nStream offset: {offset}\n      "
                        f"Tenant: {tenant_id}\n    Event ID: {event.id}\n\n-----------Attributes-----------\n\n"
                        + event.render_datatable())

                self.total_messages += 1

                if offset == self.test_end:
                    await this_consumer.unsubscribe(reactor_id)
                    await this_consumer.close()

            await consumer.start()

            if self.test_start is not None:
                offset_spec = ConsumerOffsetSpecification(OffsetType.OFFSET,
                                                          self.test_start)
            else:
                # watch mode
                offset_spec = ConsumerOffsetSpecification(OffsetType.NEXT)

            if not args.inspect:
                if args.list:
                    print(
                        f"Listing events from stream offsets {self.test_start} to {self.test_end} from stream "
                        f"{self.rmq_event_stream} on server {self.rmq_host}:{self.rmq_port}")
                else:
                    print(
                        f"Watching and reporting on events from stream {self.rmq_event_stream} on server "
                        f"{self.rmq_host}:{self.rmq_port}")
                output_header()
            await consumer.subscribe(stream=self.rmq_event_stream,
                                     callback=on_event,
                                     decoder=amqp_decoder,
                                     subscriber_name=reactor_id,
                                     offset_specification=offset_spec)

            await consumer.run()

        asyncio.run(consume())


if __name__ == '__main__':
    EventToolCLI()

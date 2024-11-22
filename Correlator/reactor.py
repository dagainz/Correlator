import argparse
import asyncio
import logging
import os
from typing import Optional, Callable, Awaitable, Any
import pickle

from rstream import (
    AMQPMessage,
    Consumer,
    ConsumerOffsetSpecification,
    OffsetType,
    MessageContext,
    amqp_decoder,
    OffsetNotFound
)

from mako.template import Template

from Correlator.config_store import RuntimeConfig, ConfigType
from Correlator.Event.core import Event
from Correlator.runtime_config import ApplicationConfig
from Correlator.core import setup_root_logger, setup_logger, ResultCodes, Instance, CredentialsReq, SimpleException, handle_config_argument
from cli import BaseCLI

log = logging.getLogger('Reactor')

ReactorConfig = [
    {
        'rabbitmq_host': {
            'default': 'docker1',
            'desc': 'The RabbitMQ server host name.',
            'type': ConfigType.STRING
        }
    },
    {
        'rabbitmq_user': {
            'default': 'guest',
            'desc': 'The RabbitMQ username',
            'type': ConfigType.STRING
        }
    },
    {
        'rabbitmq_password': {
            'default': 'guest',
            'desc': '*TRANSITIONAL* The RabbitMQ password',
            'type': ConfigType.STRING
        }
    },
      {
        'rabbitmq_event_stream': {
            'default': 'Correlator-event',
            'desc': 'The name of the RabbitMQ event stream',
            'type': ConfigType.STRING
        }
    }
]


class Reactor:
    # mako filter expressions will have these imports available to the
    # template code.

    mako_imports = [
        'from Correlator.Event.core import EventSeverity'
    ]

    # def __init__(self, config_block: dict, configuration_prefix: str):
    def __init__(self, reactor_id: str, overrides: [(str, str)]):

        self._filters = []
        # self._reactor_id = reactor_id
        self.log = log
        self._imports = {}
        self._objects = {}
        self._event_queue = []

        config_block = ApplicationConfig.reactor_by_id(reactor_id)

        tenants = config_block['tenants']
        self._reactor_id = config_block['id']

        # First pass to generate list of Python imports required to import all requested event handlers

        for tenant in tenants:
            tenant_id = tenant.get('id')
            handler_cfg = tenant.get('handlers')

            if len(handler_cfg) == 0:
                raise ValueError(f'No handlers defined for tenant {tenant_id}')

            for handler_name in handler_cfg:
                handler_section = handler_cfg[handler_name]
                (python_module, name) = handler_section['handler']
                self.log.debug(
                    f'Adding event handler {name} from python module {python_module}')
                if python_module not in self._imports:
                    self._imports[python_module] = {
                        'obj': None,
                        'names': []
                    }
                self._imports[python_module]['names'].append(name)

        # Import then
        self._import_all()

        # Instantiate handlers

        for tenant in tenants:
            tenant_id = tenant.get('id')
            handler_cfg = tenant.get('handlers')

            self._objects[tenant_id] = []

            for handler_name in handler_cfg:
                handler_section = handler_cfg[handler_name]
                fq_handler_name = f'{tenant_id}.{handler_name}'

                (python_module, name) = handler_section['handler']
                python_class = getattr(self._imports[python_module]['obj'], name)
                filter_expression = handler_section['filter_expression']
                self.log.info(
                    f'Instantiating event handler {name} from python module '
                    f'{python_module}')
                filter_template = None
                if filter_expression:
                    self.log.debug(
                        f'Processing filter expression {filter_expression}')
                    try:
                        template = Template(
                            filter_expression, imports=self.mako_imports)
                        filter_template = template
                    except Exception as e:
                        self.log.error(f'Expression parse error: {e}')
                        raise
                try:
                    obj = python_class(fq_handler_name, filter_template=filter_template)
                    self._objects[tenant_id].append(obj)
                except Exception as e:
                    self.log.error(
                        f'Could not instantiate event handler {fq_handler_name}: {e}')
                    self.log.exception(e)
                    raise

                self.log.debug('Setting handler level options')

                handler_settings = handler_section.get('config', {})
                for key, value in handler_settings.items():
                    RuntimeConfig.set(
                        f'handler.{fq_handler_name}.{key}', value)

                self.log.debug('Setting handler level overrides')
                for (key, value) in overrides:
                    if key.startswith(f'handler.{fq_handler_name}.'):
                        RuntimeConfig.set(key, value)

                try:
                    obj.initialize()
                except CredentialsReq as e:
                    for user_id in e.ids:
                        self.log.error(
                            f'Handler {fq_handler_name} missing secret for '
                            f'credential {fq_handler_name}.{user_id}')
                    raise
                except SimpleException as e:
                    self.log.error(
                        f'Handler {fq_handler_name} failed initialization: {e}')
                    raise
                except Exception as e:
                    self.log.error(
                        f'Module {fq_handler_name} failed initialization: {e}')
                    self.log.exception(e)
                    raise

    def _import_all(self):
        for module in self._imports:
            names = self._imports[module]['names']
            self.log.debug(
                f'Loading python module {module}, exposing names '
                f'{",".join(names)}')
            pkg = __import__(module, fromlist=[names])
            self._imports[module]['obj'] = pkg

    def process_event(self, record):
        event = pickle.loads(record.obj)
        self.log.info(f'Processing event {event.fq_id} for tenant {record.tenant_id}')
        handlers = self._objects.get(record.tenant_id, [])
        for handler in handlers:
            log.info(f'Checking if handler {handler.handler_name} is interested')
            wants_to_handle = False
            if handler.filter_template is not None:
                data = {'event': event}
                try:
                    res = handler.filter_template.render(**data)
                    if res == 'True':
                        log.debug('Yes, filter expression evaluated as True')
                        wants_to_handle = True
                    else:
                        log.debug('No, filter expression evaluated as False')
                except Exception as e:
                    log.debug(f'No, filter expression caught exception {e}')
                    log.exception(e)
            else:
                wants_to_handle = handler.default_action
                log.debug(
                    f'Falling through to default action of {wants_to_handle}')
            if wants_to_handle:
                handler.process_event(event)


class ReactorCLI(BaseCLI):

    def __init__(self):

        super().__init__()
        self.test_start = None
        self.test_end = None

        parser = argparse.ArgumentParser(description='Correlator Reactor')
        parser.add_argument('--id', required=True, help='Reactor ID')
        self._handle_configfile_argument(parser)

        parser.add_argument('-d', '--debug', action='store_true', help='Enable more verbose output')
        parser.add_argument('-r', '--rerun', type=self._offset_spec,
                            help='** re-runs the reactor engine against historical events according to this argument. It can be specified as an Integer or range separated by hyphen.')
        parser.add_argument(
            '--option',
            action='append',
            metavar='option.name=value',
            help='Set configuration option.name to value',
            default=[]
        )
        args = parser.parse_args()

        overrides = self._process_overrides(args)

        reactor_id = args.id
        configuration_prefix = f"reactors.{reactor_id}"

        self.log = setup_logger('Reactor', args.debug)

        if args.rerun:
            (self.test_start, self.test_end) = args.rerun

        log.info(f"Correlator {Instance.Version} {'*TEST MODE*' if args.rerun else ''} Reactor engine {reactor_id}")

        if not ApplicationConfig.load(args.config_file):
            raise ValueError('Error loading configuration file')

        config_block = ApplicationConfig.reactor_by_id(reactor_id)

        if not config_block:
            raise ValueError(f'Invalid Reactor ID: {reactor_id} found in configuration')

        # configuration_prefix = f"reactors.{reactor_id}"

        RuntimeConfig.add(ReactorConfig, configuration_prefix)

        ApplicationConfig.process_reactor_config(reactor_id)

        self.log.debug('Setting service level overrides')
        for (key, value) in overrides:
            if key.startswith('reactors.'):
                RuntimeConfig.set(key, value)

        self.rmq_host = RuntimeConfig.get(f'{configuration_prefix}.rabbitmq_host')
        self.rmq_user = RuntimeConfig.get(f'{configuration_prefix}.rabbitmq_user')

        # Need to replace with hook into keyring here

        self.rmq_password = RuntimeConfig.get(f'{configuration_prefix}.rabbitmq_password')
        self.rmq_port = 5552
        self.rmq_event_stream = RuntimeConfig.get(f'{configuration_prefix}.rabbitmq_event_stream')

        # Instantiate reactor engine with handlers

        try:
            reactor = Reactor(reactor_id, overrides)
        except ValueError as e:
            self.log.error(f'Reactor startup failed: {e}')
            raise

        self._process_overrides(args)

        RuntimeConfig.dump_to_log(self.log.info)

        # Subscribe to event stream and send received events through the reactor engine

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
                stream = this_consumer.get_stream(message_context.subscriber_name)

                obj = pickle.loads(msg.body)
                reactor.process_event(obj)

                if self.test_end is not None:
                    if offset == self.test_end:
                        await this_consumer.unsubscribe(reactor_id)
                        await this_consumer.close()
                else:
                    await this_consumer.store_offset(
                        stream=stream, offset=offset,
                        subscriber_name=message_context.subscriber_name)

            await consumer.start()

            if self.test_start is not None:
                offset_spec = ConsumerOffsetSpecification(OffsetType.OFFSET, self.test_start)
                log.info(f'Subscribing to event stream {self.rmq_event_stream} starting at offset {self.test_start}')
            else:
                try:
                    offset = await consumer.query_offset(stream=self.rmq_event_stream, subscriber_name=reactor_id)
                    new_offset = offset + 1
                    offset_spec = ConsumerOffsetSpecification(OffsetType.OFFSET, new_offset)
                    log.info(f'Subscribing to event stream {self.rmq_event_stream} starting at offset {new_offset}')
                except OffsetNotFound:
                    offset_spec = ConsumerOffsetSpecification(OffsetType.NEXT)
                    log.info(f'Subscribing to event stream {self.rmq_event_stream} and starting at the end')

            await consumer.subscribe(stream=self.rmq_event_stream,
                                     callback=on_event,
                                     decoder=amqp_decoder,
                                     subscriber_name=reactor_id,
                                     offset_specification=offset_spec)

            await consumer.run()

        asyncio.run(consume())


if __name__ == '__main__':
    ReactorCLI()

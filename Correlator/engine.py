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
)

from Correlator.config_store import RuntimeConfig, ConfigType
from Correlator.Event.core import Event
from Correlator.runtime_config import ApplicationConfig
from Correlator.core import setup_root_logger, RecordTypes, ResultCodes, Instance, CredentialsReq, SimpleException

import grpc
import mediator_pb2_grpc
import mediator_pb2

from typing import Union, List
# for pickle
from Sources.TCP_Syslog.tcp_syslog_source import SyslogRecord

log = logging.getLogger(__name__)

EngineConfig = [
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
        'rabbitmq_input_stream': {
            'default': 'Correlator-input',
            'desc': 'The name of the RabbitMQ input stream',
            'type': ConfigType.STRING
        }
    },
    {
        'rabbitmq_event_stream': {
            'default': 'Correlator-event',
            'desc': 'The name of the RabbitMQ event stream',
            'type': ConfigType.STRING
        }
    },
    {
        'mediator_endpoint': {
            'default': '127.0.0.1:50051',
            'desc': 'The address and port of the Correlator mediator service',
            'type': ConfigType.STRING
        }
    },
    {
        'persistence_store': {
            'default': '/',
            'desc': 'Writable directory for store files',
            'type': ConfigType.STRING
        }
    },
    {
        'save_store_interval': {
            'default': 10000,
            'desc': 'Source record interval between store saves',
            'type': ConfigType.INTEGER
        }
    }

]


class Engine:

    def __init__(self, config_block: dict, configuration_prefix: str, engine_id: str, store_dir: str, reset_store: bool):

        self._filters = []
        self._engine_id = engine_id
        self.log = log
        self._imports = {}
        self._objects = {}
        self._full_store = None
        self._event_queue = []

        self.source_stream_offset = None
        self.event_stream_offset = None

        self.records_since_save = None
        self.first_event = True

        self._really_send_events = True

        if not os.access(store_dir, os.W_OK):
            raise ValueError('Persistence store folder does not exist or is not writable')

        self._store_dir = store_dir
        self._store_filename = os.path.join(f'{engine_id}.store')
        self._store_fullpath = os.path.join(self._store_dir, self._store_filename)
        self._save_store_interval =  RuntimeConfig.get(f"{configuration_prefix}.save_store_interval")

        # First pass through tenants to collect list of Python modules to dynamically import

        mediator_endpoint = RuntimeConfig.get(f"{configuration_prefix}.mediator_endpoint")
        self._grpc_channel = grpc.insecure_channel(mediator_endpoint)

        self.log.info(f'Connected to mediator service at {mediator_endpoint}')

        self._stub = mediator_pb2_grpc.MediatorStub(self._grpc_channel)

        tenants = config_block['tenants']
        for tenant in tenants:
            tenant_id = tenant.get('id')
            modules = tenant.get('modules')
            # module_cfg = app['modules']
            if len(modules) == 0:
                raise ValueError(f'No modules defined for tenant {tenant_id}')

            for module_name in modules:
                module_section = modules[module_name]
                (python_module, name) = module_section['module']
                if python_module not in self._imports:
                    self._imports[python_module] = {
                        'obj': None,
                        'names': []
                    }
                self._imports[python_module]['names'].append(name)

        # Import python modules
        self._import_all()

        if reset_store:
            if not os.remove(self._store_fullpath):
                self.log.error(f'Could not remove store file {self._store_fullpath}')

        # Initialize the persistence store

        self._load_store()

        # Second pass to instantiate all modules for all tenants

        for tenant in tenants:
            tenant_id = tenant.get('id')
            modules = tenant.get('modules')

            self._objects[tenant_id] = []

            for module_name in modules:

                module_section = modules[module_name]
                fq_module_name = f'{tenant_id}.{module_name}'

                (python_module, name) = module_section['module']

                self.log.info(f'Instantiating module {name} from python module {python_module} as {fq_module_name}')

                python_class = getattr(self._imports[python_module]['obj'], name)

                def event_dispatcher(event):
                    nonlocal tenant_id
                    self._event_queue.append([tenant_id, event])
                    self.log.info(f'Event {tenant_id}:{event.fq_id} added to queue')

                module = python_class(fq_module_name, event_dispatcher)
                self._objects[tenant_id].append(module)

                self.log.debug('Setting module level options')

                module_settings = module_section.get('config', {})
                for key, value in module_settings.items():

                    RuntimeConfig.set(
                        f'module.{fq_module_name}.{key}', value)
                self.log.debug('Initializing store and module')
                if fq_module_name not in self._full_store:
                    self._full_store[fq_module_name] = module.model()
                module.store = self._full_store[fq_module_name]
                try:
                    module.initialize()
                except CredentialsReq as e:
                    for user_id in e.ids:
                        self.log.error(
                            f'Module {module.module_name} missing secret for '
                            f'credential {module.module_name}.{user_id}')
                    raise
                except SimpleException as e:
                    self.log.error(
                        f'Module {module.module_name} failed initialization: {e}')
                    raise
                except Exception as e:
                    self.log.error(
                        f'Module {module.module_name} failed initialization: {e}')
                    self.log.exception(e)
                    raise
                module.post_init_store()

    def _import_all(self):
        for module in self._imports:
            names = self._imports[module]['names']
            self.log.debug(
                f'Loading python module {module}, exposing names '
                f'{",".join(names)}')
            pkg = __import__(module, fromlist=[names])
            self._imports[module]['obj'] = pkg

    def _send_events(self) -> None:
        if not self._really_send_events:
            log.info('Fake sending events to mediator')
            # if self._event_queue:
            self._event_queue = []
        else:
            for tenant, event in self._event_queue:
                log.info(f'Sending event {tenant}:{event.fq_id} to mediator service')
                response = self._stub.DispatchEvent(mediator_pb2.EventRecord(
                    tenant_id=tenant,
                    obj=pickle.dumps(event)))
                message = f'Server responded with {response.message}, Code: {response.code}'
                if response.code != 0:
                    log.error(message)
                else:
                    log.info(message)
            self._event_queue = []

    def _load_store(self):
        try:
            with open(self._store_fullpath, 'rb') as input_file:
                self._full_store = pickle.load(input_file)
                log.info(f'Load store: Store loaded from file {self._store_filename}.')
                self.source_stream_offset = self._full_store['_source_stream_offset']
                self.event_stream_offset = self._full_store['_event_stream_offset']

        except FileNotFoundError:
            log.info(f'Load store: Store file  {self._store_filename} does not exist')
            self.source_stream_offset = 0
            self.event_stream_offset = 0
            self._full_store = {
                '_source_stream_offset': 0,
                '_event_stream_offset': 0
            }
        finally:
            log.info(
                f'Restored offsets: Source: {self.source_stream_offset}, Event: {self.event_stream_offset}')

    def save_store(self, reason: str):

        with open(self._store_fullpath, 'wb') as output_file:
            self._full_store['_source_stream_offset'] = self.source_stream_offset
            self._full_store['_event_stream_offset'] = self.event_stream_offset
            pickle.dump(self._full_store, output_file, 0)
            log.info(f'Save store: store written to {self._store_filename} because {reason}')
            self.records_since_save = 0

            return True

    def process_record(self, record):

        # self.log.info(f'Processing record for tenant {record.tenant_id}')
        modules = self._objects.get(record.tenant_id, [])
        for module in modules:
            module.handle_record(pickle.loads(record.obj))

        if self._event_queue:
            self._send_events()
            self.save_store('Post event')
        elif self.records_since_save is None:
            self.save_store('First record')
        elif self.records_since_save == self._save_store_interval:
            self.save_store('Interval')
        else:
            self.records_since_save += 1

    def process_event(self, record):
        event = pickle.loads(record.obj)
        self.log.info(f'Processing event {event.fq_id} for tenant {record.tenant_id}')
        modules = self._objects.get(record.tenant_id, [])
        for module in modules:
            module.handle_event(event)
        if self._event_queue:
            self._send_events()
            self.save_store('Post event')


class CLI:

    def __init__(self):
        self.log = log

        parser = argparse.ArgumentParser(description='Correlation engine.')
        parser.add_argument('--id', required=True, help='Engine ID')
        parser.add_argument(
            '--config_file',
            required=True,
            help='Configuration file to use'
        )
        parser.add_argument('-d', '--debug', action='store_true', help='Enable more verbose output')
        parser.add_argument('--reset', action='store_true', help='Clear persistence store and start over')

        args = parser.parse_args()

        if 'CORRELATOR_CFG' in os.environ:
            final_config_file = os.environ['CORRELATOR_CFG']
            self.log.debug(f'CORRELATOR_CFG environment variable set. Using its'
                           f' value of  {final_config_file}')
        else:
            final_config_file = args.config_file
            self.log.debug(f'CORRELATOR_CFG environment variable not set.'
                           f' Using the preset value of {final_config_file}')

        if not ApplicationConfig.load(final_config_file):
            raise ValueError('Cannot load configuration file')

        config_block = ApplicationConfig.engine_by_id(args.id)

        if not config_block:
            raise ValueError(f'No engine with ID {args.id} found in configuration')

        if args.debug:
            level = logging.DEBUG
        else:
            level = logging.INFO

        setup_root_logger(level)

        configuration_prefix = f"engines.{args.id}"

        RuntimeConfig.add(EngineConfig, configuration_prefix)

        ApplicationConfig.process_engine_config(args.id)
        try:
            self.rmq_host = RuntimeConfig.get(f'{configuration_prefix}.rabbitmq_host')
            self.rmq_user = RuntimeConfig.get(f'{configuration_prefix}.rabbitmq_user')

            # Need to replace with hook into keyring here

            self.rmq_password = RuntimeConfig.get(
                f'{configuration_prefix}.rabbitmq_password')
            self.rmq_port = 5552
            self.rmq_input_stream = RuntimeConfig.get(f'{configuration_prefix}.rabbitmq_input_stream')
            self.rmq_event_stream = RuntimeConfig.get(f'{configuration_prefix}.rabbitmq_event_stream')

            self.store_directory = RuntimeConfig.get(f'{configuration_prefix}.persistence_store')

            engine = Engine(config_block, configuration_prefix, args.id, self.store_directory, args.reset)

            RuntimeConfig.dump_to_log()

            async def consume():
                consumer = Consumer(
                    host=self.rmq_host,
                    port=self.rmq_port,
                    vhost="/",
                    username=self.rmq_user,
                    password=self.rmq_password,
                )

                # loop = asyncio.get_event_loop()
                # loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(
                #   consumer.close()))

                async def on_message(msg: AMQPMessage,
                                     message_context: MessageContext):
                    stream = message_context.consumer.get_stream(
                        message_context.subscriber_name)

                    engine.source_stream_offset = message_context.offset
                    obj = pickle.loads(msg.body)
                    engine.process_record(obj)
                    # engine.save_store()

                async def on_event(msg: AMQPMessage,
                                   message_context: MessageContext):
                    stream = message_context.consumer.get_stream(
                        message_context.subscriber_name)

                    engine.event_stream_offset = message_context.offset

                    obj = pickle.loads(msg.body)
                    engine.process_event(obj)
                    # engine.save_store()

                await consumer.start()

                if engine.source_stream_offset != 0:
                    source_offset = engine.source_stream_offset + 1
                    source_spec = ConsumerOffsetSpecification(OffsetType.OFFSET, source_offset)
                    log.info(f'Subscribing to source stream {self.rmq_input_stream} starting at offset {source_offset}')
                else:
                    source_spec = ConsumerOffsetSpecification(OffsetType.NEXT)
                    log.info(f'Subscribing to source stream {self.rmq_input_stream} and starting at the end')

                if engine.event_stream_offset != 0:
                    event_offset = engine.event_stream_offset + 1
                    event_spec = ConsumerOffsetSpecification(OffsetType.OFFSET, event_offset)
                    log.info(f'Subscribing to event stream {self.rmq_event_stream} starting at offset {event_offset}')
                else:
                    event_spec = ConsumerOffsetSpecification(OffsetType.NEXT)
                    log.info(f'Subscribing to event stream {self.rmq_event_stream} and starting at the end')

                # log.info(f'Connected to RabbitMQ. Source stream: {self.rmq_input_stream}, Event stream: '
                #          f'{self.rmq_event_stream}')

                await consumer.subscribe(stream=self.rmq_input_stream,
                                         callback=on_message,
                                         decoder=amqp_decoder,
                                         offset_specification=source_spec)

                await consumer.subscribe(stream=self.rmq_event_stream,
                                         callback=on_event,
                                         decoder=amqp_decoder,
                                         offset_specification=event_spec)

                await consumer.run()

            asyncio.run(consume())
        except ValueError as e:
            log.error(f'Invalid configuration: {e}')


if __name__ == '__main__':
    CLI()

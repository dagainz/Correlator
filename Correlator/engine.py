import argparse
import asyncio
import logging
import os
from typing import Optional, Callable, Awaitable, Any
import pickle

from rstream import (
    AMQPMessage,
    Consumer,
    MessageContext,
    amqp_decoder,
)

from Correlator.config_store import RuntimeConfig, ConfigType
from Correlator.app_config import ApplicationConfig
from Correlator.core import setup_root_logger, RecordTypes, ResultCodes, Instance

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
    }

]


class Engine:
    def __init__(self, config_block: dict, store_dir: str):

        self._filters = []
        self.log = log
        self._imports = {}
        self._objects = {}
        self._full_store = {}
        if store_dir is not None and not os.access(store_dir, os.W_OK):
            raise ValueError('Store folder is not writable')

        # store_dir either None or writeable directory

        self._store_dir = store_dir

        # First pass through tenants to collect list of Python modules to dynamically import

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

                module = python_class(fq_module_name)
                self._objects[tenant_id].append(module)

                self.log.debug('Setting module level options')

                module_settings = module_section.get('config', {})
                for key, value in module_settings.items():

                    RuntimeConfig.set(
                        f'module.{fq_module_name}.{key}', value)
                self.log.debug('Initializing store and module')
                if module.module_name not in self._full_store:
                     self._full_store[module.module_name] = module.model()
                module.store = self._full_store[module.module_name]
                module.post_init_store()


    def _import_all(self):
        for module in self._imports:
            names = self._imports[module]['names']
            self.log.debug(
                f'Loading python module {module}, exposing names '
                f'{",".join(names)}')
            pkg = __import__(module, fromlist=[names])
            self._imports[module]['obj'] = pkg

    def process_record(self, record):

        # self.log.info(f'Record: {record}')
        modules = self._objects.get(record.tenant_id, [])
        for module in modules:
            module.handle_record(pickle.loads(record.obj))



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

        cfgblock = ApplicationConfig.engine_by_id(args.id)

        if not cfgblock:
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

            engine = Engine(cfgblock, None)

        except ValueError as e:
            log.error(f'Invalid configuration: {e}')
            return

        self._engine_desc = cfgblock.get('desc')
        log.info(f"Correlator {Instance.Version} Correlation Engine '{self._engine_desc}' (id: [{args.id}]) startup")

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

            async def on_message(msg: AMQPMessage, message_context: MessageContext):
                stream = message_context.consumer.get_stream(message_context.subscriber_name)
                offset = message_context.offset

                obj = pickle.loads(msg.body)
                engine.process_record(obj)
#
            await consumer.start()
            log.info('Connected to RabbitMQ')
            await consumer.subscribe(stream=self.rmq_input_stream, callback=on_message, decoder=amqp_decoder)
            # await consumer.subscribe(stream=STREAM2, callback=on_message_2,
            #                          decoder=amqp_decoder)
            await consumer.run()

        asyncio.run(consume())


if __name__ == '__main__':
    CLI()

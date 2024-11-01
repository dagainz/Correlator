"""Support for Correlator application configuration and setup.

While confusing, there are two configuration systems. This is the one that
handles Correlator applications - A collection of modules, event handlers,
and configuration that define them.

"""

import logging
import json
from mako.template import Template
from schema import Schema, Optional

from Correlator.Event.core import EventProcessor
from Correlator.config_store import RuntimeConfig
from Correlator.core import CredentialsReq, SimpleException


class CorrelatorStack:
    def __init__(self, processor, modules):
        self.processor = processor
        self.modules = modules


class ApplicationConfigStore:
    # system configuration schema

    config_schema = Schema({
        'name': str,
        'input_processor': {
            str: object
        },
        'sources': [
            {
                'id': str,
                'desc': str,
                'connector': str,
                Optional('config', default={}): {
                    str: object
                }
            }

        ],
        'engines': [
            {
                'id': str,
                'desc': str,
                Optional('config', default={}): {
                    str: object

                },
                'tenants': [
                    {
                        'id': str,
                        'modules': {
                            str: {
                                'module': [str, str],
                                Optional('config', default={}): {
                                    str: object

                                }
                            }
                        }
                    }
                ]
            }
        ],
        'handlers': {
            str: {
                'handler': [str, str],
                Optional('filter_expression', default=''): str,
                Optional('config', default={}): {
                    str: object
                }
            }
        }
    })

    # mako filter expressions will have these imports available to the
    # template code.

    mako_imports = [
        'from Correlator.Event.core import EventSeverity'
    ]

    def __init__(self):
        self.loaded = False
        self.cfg = None
        self.imports = {}
        self.log = logging.getLogger('ApplicationConfigStore')
        self._source_by_id = {}
        self._engine_by_id = {}

    def load(self, filename: str):

        self.log.debug(f'Loading configuration file [{filename}]')
        try:
            with open(filename) as f:
                parsed_json = json.load(f)
                cfg = self.config_schema.validate(parsed_json)
                # self.log.debug('Setting system level options')
                # system_settings = cfg['system']['config']
                # for key in system_settings:
                #     RuntimeConfig.set(key, system_settings[key])
                sources = cfg.get('sources', [])
                for source in sources:
                    # todo validate source (maybe)
                    self._source_by_id[source['id']] = source

                engines = cfg.get('engines', [])
                for engine in engines:
                    # todo validate engine (maybe)
                    self._engine_by_id[engine['id']] = engine

        except Exception as e:
            self.log.error(f'Configuration error: {e}')
            return False

        self.cfg = cfg
        return True

    def source_by_id(self, source_id: str):
        return self._source_by_id.get(source_id)

    def engine_by_id(self, engine_id: str):
        return self._engine_by_id.get(engine_id)

    def process_section_config(self, section: str):
        self.log.info(f'Processing configuration section [{section}]')
        settings = self.cfg.get(section)
        if settings:
            for relative_key in settings:
                key = f'{section}.{relative_key}'
                value = settings[key]
                self.log.debug(f'Setting {key} to {value}')
                RuntimeConfig.set(key, value)
        else:
            self.log.debug('No configuration found')

    def process_source_config(self, source_id: str):
        self.log.info(f'Processing configuration for source {source_id}')
        source = self.source_by_id(source_id)
        if source:
            settings = source.get('config', {})
            for relative_key in settings:
                key = f'sources.{source_id}.{relative_key}'
                value = settings[relative_key]
                self.log.debug(f'Setting {key} to {value}')
                RuntimeConfig.set(key, value)

    def process_engine_config(self, engine_id: str):
        self.log.info(f'Processing configuration for engine {engine_id}')
        engine = self.engine_by_id(engine_id)
        if engine:
            settings = engine.get('config', {})
            for relative_key in settings:
                key = f'engines.{engine_id}.{relative_key}'
                value = settings[relative_key]
                self.log.debug(f'Setting {key} to {value}')
                RuntimeConfig.set(key, value)

    def add_module(self, module, name):
        if module not in self.imports:
            self.imports[module] = {
                'obj': None,
                'names': [name]
            }
            return

        self.imports[module]['names'].append(name)

    def import_all(self):
        for module in self.imports:
            names = self.imports[module]['names']
            self.log.debug(
                f'Loading python module {module}, exposing names '
                f'{",".join(names)}')
            pkg = __import__(module, fromlist=[names])
            self.imports[module]['obj'] = pkg

    def apps(self):
        apps = self.cfg.get('application', {})
        for app in apps:
            desc = apps[app]['description']
            yield app, desc

    def build_stack(self, app_name: str, cmdline_options: list[
        list[str, str]]) -> CorrelatorStack | None:

        self.log.debug('build_stack')
        apps = self.cfg.get('application', {})
        app = apps.get(app_name)
        if not app:
            self.log.error(f'Application {app_name} not found in configuration')
            return None

        # Prepare list of Modules

        module_cfg = app['modules']
        if len(module_cfg) == 0:
            self.log.error('No modules defined')
            return None

        for module_name in module_cfg:
            module_section = module_cfg[module_name]
            (python_module, name) = module_section['module']
            self.log.debug(
                f'Adding module {name} from python module {python_module}')
            self.add_module(python_module, name)

        # app_settings = app['config']

        handler_cfg = app['handlers']

        if len(handler_cfg) == 0:
            self.log.error('No handlers defined')
            return None

        for handler_name in handler_cfg:
            handler_section = handler_cfg[handler_name]
            (python_module, name) = handler_section['handler']
            self.log.debug(
                f'Adding event handler {name} from python module '
                f'{python_module}')
            self.add_module(python_module, name)

        # Perform imports

        self.import_all()

        # Instantiate modules

        module_objects = []

        for module_name in module_cfg:
            module_section = module_cfg[module_name]
            (python_module, name) = module_section['module']
            self.log.info(
                f'Instantiating module {name} from python module '
                f'{python_module} as {module_name}')
            python_class = getattr(self.imports[python_module]['obj'], name)
            module_objects.append(python_class(module_name))
            self.log.debug('Setting module level options')
            module_settings = module_section.get('config', {})
            for key in module_settings:
                RuntimeConfig.set(
                    f'module.{module_name}.{key}', module_settings[key])

        handler_objects = []

        # Instantiate handlers

        for handler_name in handler_cfg:
            handler_section = handler_cfg[handler_name]
            (python_module, name) = handler_section['handler']
            python_class = getattr(self.imports[python_module]['obj'], name)
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
                    return None
            try:
                handler_objects.append(
                    python_class(handler_name, filter_template=filter_template))
            except Exception as e:
                self.log.error(
                    f'Could not instantiate event handler {handler_name}: {e}')
                self.log.exception(e)
                return None

            self.log.debug('Setting handler level options')
            handler_settings = handler_section.get('config', {})
            for key in handler_settings:
                RuntimeConfig.set(
                    f'handler.{handler_name}.{key}', handler_settings[key])

        self.log.debug('Setting command line level options')
        for (key, value) in cmdline_options:
            RuntimeConfig.set(key, value)

        # Initialize modules and handlers, and build event processor

        processor = EventProcessor()
        required_creds = []

        for module in module_objects:
            try:
                module.initialize()
            except CredentialsReq as e:
                for user_id in e.ids:
                    self.log.error(
                        f'Module {module.module_name} missing secret for '
                        f'credential {module.module_name}.{user_id}')
                return None
            except SimpleException as e:
                self.log.error(
                    f'Module {module.module_name} failed initialization: {e}')
                return None
            except Exception as e:
                self.log.error(
                    f'Module {module.module_name} failed initialization: {e}')
                self.log.exception(e)
                return None

        for handler in handler_objects:
            try:
                handler.initialize()
            except CredentialsReq as e:
                for user_id in e.ids:
                    self.log.error(
                        f'Handler missing secret for credential '
                        f'{handler.handler_name}.{user_id}')
                return None
            except SimpleException as e:
                self.log.error(
                    f'Handler {handler.handler_name} failed initialization: '
                    f'{e}')
                return None
            except Exception as e:
                self.log.error(
                    f'Handler {handler.handler_name} raised an unexpected '
                    f'exception during initialization: {e}')
                self.log.exception(e)
                return None

            processor.register_listener(handler)

        return CorrelatorStack(processor, module_objects)


ApplicationConfig = ApplicationConfigStore()

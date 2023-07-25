import json
import logging
import re
from mako.template import Template
from schema import Schema, Optional
from typing import List

from Correlator.Event.core import EventProcessor

log = logging.getLogger(__name__)


class ConfigType:

    types = {
        1: 'Integer',
        2: 'Float',
        3: 'String',
        4: 'Boolean',
        5: 'Bytes',
        6: 'Email'}

    INTEGER: int = 1
    FLOAT: int = 2
    STRING: int = 3
    BOOLEAN: int = 4
    BYTES: int = 5
    EMAIL: int = 6

    @classmethod
    def text(cls, code):
        return cls.types.get(code, 'Unknown')


class ConfigException(Exception):
    pass


BaseSystemConfig = [
    {
        'run_dir': {
            'default': '/var/run',
            'desc': 'Writable folder for internal files',
            'type': ConfigType.STRING
        }
    }
]


class ConfigStore:
    def __init__(self):

        self.store = {}

    def add(self, item, prefix: str, instance: str = None):

        if isinstance(item, list):
            items = item
        else:
            items = [item]

        for item in items:
            for key in item:
                if item[key].get('type') is None:
                    raise ConfigException(f'{key}: No type definition')

                # Rename key, adding prefix and instance, if applicable

                new_item = {}

                if instance is not None:
                    new_key = f'{prefix}.{instance}.{key}'
                else:
                    new_key = f'{prefix}.{key}'

                new_item[new_key] = item[key]
                log.debug(f'Configuration item {key} added as {new_key}')
                self.store.update(new_item)

    def _assert_parameter(self, parameter):
        if parameter not in self.store:
            raise ConfigException(f'Unknown configuration parameter: {parameter}')

    def set(self, parameter: str, value):
        log.debug(f'Set configuration parameter {parameter} to {value}')

        # Ensure this is a valid parameter
        self._assert_parameter(parameter)

        if isinstance(value, str):
            value_cmp = value.lower()
        else:
            value_cmp = value

        config_type = self.store[parameter].get('type')

        message = ''

        if not config_type:
            message = "No config type"

        set_value = None

        if config_type == ConfigType.BOOLEAN:
            if value_cmp in (0, 'false', 'no', False):
                set_value = False
            elif value_cmp in (1, 'true', 'yes', True):
                set_value = True
            else:
                message = f'{value} does not map to a valid boolean'
        elif config_type == ConfigType.INTEGER:
            try:
                set_value = int(value)
            except ValueError:
                message = f'{value} will not cast to a valid integer'
        elif config_type == ConfigType.EMAIL:
            if not re.match(r'^[A-Z0-9+_.-]+@[A-Z0-9.-]+$', value):
                message = f'{value} is not a valid email address'
            else:
                set_value = value
        elif config_type == ConfigType.FLOAT:
            try:
                set_value = float(value)
            except ValueError as v:
                message = f'{value} will not cast to a valid float'
        elif config_type == ConfigType.BYTES:
            if not isinstance(value, bytes):
                set_value = str(value).encode('utf-8')
        else:       # ConfigType.STRING
            set_value = str(value)

        if set_value is None:
            raise ConfigException(f'{parameter}: {message}')

        self.store[parameter]['value'] = set_value

    def get(self, parameter: str):
        self._assert_parameter(parameter)
        v = self.store[parameter].get(
            'value', self.store[parameter].get('default'))

        return v

    def get_values(self, parameters: list):
        ret = []
        for parameter in parameters:
            self._assert_parameter(parameter)
            ret.append(
                self.store[parameter].get(
                    'value', self.store[parameter].get('default')))
        return ret

    def list(self):
        """Returns list of list all configuration parameters

        Plus the description, the current value, and the default value

        [
            [parameter, description, default value, current value]
        ]

        """

        return [
            [x,
             self.store[x].get('desc'),
             self.store[x].get('default'),
             self.store[x].get('value', self.store[x].get('default')),
             ConfigType.text(self.store[x].get('type', 0))
             ] for x in self.store
        ]

    @staticmethod
    def dump_to_log(debug=True):
        
        if debug:
            log_obj = log.debug
        else:
            log_obj = log.info

        log_obj(f'{"Parameter":<45} {"Type":<10} {"Value":<10} {"Default":<10} '
                  f'{"Description":<14}')
        log_obj(f'{"---------":<45} {"------":<10} {"------":<10} '
                f'{"-------":<10} {"-----------------------":<14}')
        for (parameter, description, default, current,
             datatype) in GlobalConfig.list():
            log_obj(
                f'{parameter or "":<45} {datatype:<10} '
                f'{repr(current or ""):<10} {repr(default or ""):<10} '
                f'{description or "":<14}')


GlobalConfig = ConfigStore()
GlobalConfig.add(BaseSystemConfig, 'system')


def config_list_to_md(config_list: list):
    """Generate a Markdown table from a Configuration Item list"""

    output = '| Key | Description | Type | Default value |\n'
    output += '|-----|-------------|------|---------------|\n'

    for config_dict in config_list:
        for config_key in config_dict:
            config_item = config_dict[config_key]
            config_type = config_item.get("type", ConfigType.INTEGER)
            if config_type in (ConfigType.STRING, ConfigType.BYTES):
                default_value = repr(config_item.get('default'))
            else:
                default_value = config_item.get('default')
            config_desc = config_item.get('desc')
            type_string = ConfigType.types[config_type]

            output += (f'| {config_key} | {config_desc} | {type_string} | '
                       f'{default_value} |\n')

    return output


class CorrelatorStack:
    def __init__(self, processor, modules):
        self.processor = processor
        self.modules = modules


class BaseConfig:

    config_schema = Schema({
        'system': {
            Optional('config', default={}): {
                str: object
            }
        },
        'application': {
            str: {
                'modules': {
                    str: {
                        'module': [str, str],
                        Optional('config', default={}): {
                            str: object
                        }
                    },
                },
                'handlers': {
                    str: {
                        'handler': [str, str],
                        'filter_expression': str,
                        Optional('config', default={}): {
                         str: object
                        }
                    }
                }
            }
        }
    })

    # mako filter expressions will have these imports available to the
    # template code.

    mako_imports = [
        'from Correlator.Event.core import EventType, EventStatus'
    ]

    def __init__(self):
        self.loaded = False
        self.cfg = None
        self.imports = {}

    def load(self, filename: str):

        log.debug(f'Loading configuration file [{filename}]')
        try:
            with open(filename) as f:
                parsed_json = json.load(f)
                cfg = self.config_schema.validate(parsed_json)
                log.debug('Setting system level options')
                system_settings = cfg['system']['config']
                for key in system_settings:
                    GlobalConfig.set(key, system_settings[key])
                    # log.debug(f'Set [{key}] to [{system_settings[key]}]')

        except Exception as e:
            log.error(f'Configuration error: {e}')
            return False

        self.cfg = cfg
        return True

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
            log.debug(f'Loading python module {module}, exposing names {",".join(names)}')
            pkg = __import__(module, fromlist=[names])
            self.imports[module]['obj'] = pkg

    def build_stack(self, app_name: str, cmdline_options: list[list[str, str]]) -> CorrelatorStack | None:

        log.debug('build_stack')
        apps = self.cfg.get('application', {})
        app = apps.get(app_name)
        if not app:
            log.error(f'Application {app_name} not found in configuration')
            return None

        # Prepare list of Modules

        module_cfg = app['modules']
        if len(module_cfg) == 0:
            log.error('No modules defined')
            return None

        for module_name in module_cfg:
            module_section = module_cfg[module_name]
            (python_module, name) = module_section['module']
            log.info(f'Adding Correlator module {name} from python module {python_module}')
            self.add_module(python_module, name)

        # app_settings = app['config']

        handler_cfg = app['handlers']

        if len(handler_cfg) == 0:
            log.error('No handlers defined')
            return None

        for handler_name in handler_cfg:
            handler_section = handler_cfg[handler_name]
            (python_module, name) = handler_section['handler']
            log.info(f'Adding event handler {name} from python module {python_module}')
            self.add_module(python_module, name)

        # Perform imports

        self.import_all()

        # log.debug('Setting application level options')
        # for key in app_settings:
        #     GlobalConfig.set(key, app_settings[key])
        #     # log.debug(f'Set [{key}] to [{app_settings[key]}]')


        # Instantiate modules

        module_objects = []

        for module_name in module_cfg:
            module_section = module_cfg[module_name]
            (python_module, name) = module_section['module']
            log.info(f'Instantiating Correlator module {name} from python module {python_module} as {module_name}')
            python_class = getattr(self.imports[python_module]['obj'], name)
            module_objects.append(python_class(module_name))
            log.debug('Setting module level options')
            module_settings = module_section.get('config', {})
            for key in module_settings:
                GlobalConfig.set(f'module.{module_name}.{key}', module_settings[key])
                # log.debug(f'Set [{key}] to [{module_settings[key]}]')

        handler_objects = []

        # Instantiate handlers

        for handler_name in handler_cfg:
            handler_section = handler_cfg[handler_name]
            (python_module, name) = handler_section['handler']
            python_class = getattr(self.imports[python_module]['obj'], name)
            filter_expression = handler_section['filter_expression']
            log.info(f'Instantiating event handler {name} from python module {python_module}')
            if filter_expression:
                log.info(f'Adding filter expression {filter_expression}')
                try:
                    template = Template(filter_expression, imports=self.mako_imports)
                    # processor.register_listener(python_class(handler_name, filter_template=template))
                    handler_objects.append(python_class(handler_name, filter_template=template))
                except Exception as e:
                    log.error(f'Something bad happened: {e}')
                    return None
            else:
                handler_objects.append(python_class(handler_name))
                # processor.register_listener(python_class(handler_name))

            log.debug('Setting handler level options')
            handler_settings = handler_section.get('config', {})
            for key in handler_settings:
                GlobalConfig.set(f'handler.{handler_name}.{key}', handler_settings[key])
                # log.debug(f'Set [{key}] to [{module_settings[key]}]')

        log.debug('Setting command line level options')
        for (key, value) in cmdline_options:
            GlobalConfig.set(key, value)
            # log.debug(f'Set [{key}] to [{value}]')

        # Initialize modules and handlers, and build event processor

        processor = EventProcessor()

        for module in module_objects:
            module.initialize()

        for handler in handler_objects:
            handler.initialize()
            processor.register_listener(handler)

        return CorrelatorStack(processor, module_objects)


SystemConfig = BaseConfig()

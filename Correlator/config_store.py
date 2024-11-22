"""Support for the runtime configuration store.

While confusing, there are two configuration systems. This is the one that
handles the runtime configuration store that the system, modules, and event
handlers use during execution.

"""
import copy
import logging
import re


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


BaseSystemConfig = [
    {
        'run_dir': {
            'default': '/var/spool/correlator',
            'desc': 'Writable folder for internal files',
            'type': ConfigType.STRING
        }
    }
]


class ConfigStore:
    """Provides run-time functionality for the configuration store

    """
    def __init__(self):

        self.store = {}
        self.log = logging.getLogger('ConfigStore')

    def add(self, item, prefix: str, instance: str = None):
        """Add a configuration item or block to the store"""

        if isinstance(item, list):
            items = item
        else:
            items = [item]

        for item in items:
            for key in item:
                if item[key].get('type') is None:
                    raise ValueError(f'{key}: No type definition')

                # Rename key, adding prefix and instance, if applicable

                new_item = {}

                if instance is not None:
                    new_key = f'{prefix}.{instance}.{key}'
                else:
                    new_key = f'{prefix}.{key}'

                new_item[new_key] = copy.deepcopy(item[key])
                self.log.debug(f'Configuration item {key} added as {new_key}')
                self.store.update(new_item)

    def _assert_parameter(self, parameter):
        if parameter not in self.store:
            raise ValueError(f'Unknown configuration parameter: {parameter}')

    def set(self, parameter: str, value):
        """Attempts to set a configuration parameter to a certain value.

        It will cast if it can, or raise an exception if it cannot be
        set for any reason.

        """

        self.log.debug(f'Set configuration parameter {parameter} to {value}')

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
            if not re.match(r'^[A-Z0-9+_.-]+@[A-Z0-9.-]+$', value,
                            re.IGNORECASE):
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
            raise ValueError(f'{parameter}: {message}')

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

    def dump_to_log(self, log_obj):

        log_obj(f'{"Parameter":<45} {"Type":<10} {"Value":<10} {"Default":<10} '
                f'{"Description":<14}')
        log_obj(f'{"---------":<45} {"------":<10} {"------":<10} '
                f'{"-------":<10} {"-----------------------":<14}')
        for (parameter, description, default, current,
             datatype) in RuntimeConfig.list():
            log_obj(
                f'{parameter or "":<45} {datatype:<10} '
                f'{repr(current or ""):<10} {repr(default or ""):<10} '
                f'{description or "":<14}')


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


# Initialize the globally accessible instance that is usable throughout

RuntimeConfig = ConfigStore()
RuntimeConfig.add(BaseSystemConfig, 'system')

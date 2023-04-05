import logging
import re
from typing import List
from dataclasses import dataclass

log = logging.getLogger(__name__)


class ConfigType:

    types: List[str] = [
        'Unknown',
        'Integer',
        'Float',
        'String',
        'Boolean',
        'Bytes',
        'Email'
    ]

    INTEGER: int = 1
    FLOAT: int = 2
    STRING: int = 3
    BOOLEAN: int = 4
    BYTES: int = 5
    EMAIL: int = 6

    @classmethod
    def text(cls, code):
        return cls.types[code]


class ConfigStore:
    def __init__(self):
        self.store = {}

    def add(self, item):

        if isinstance(item, list):
            items = item
        else:
            items = [item]

        for item in items:
            for key in item:
                if item[key].get('type') is None:
                    raise ValueError(f'{key}: No type definition')
            self.store.update(item)

    def _assert_parameter(self, parameter):
        if parameter not in self.store:
            raise ValueError(f'Unknown configuration parameter: {parameter}')

    def set(self, parameter: str, value):

        # Ensure this is a valid parameter
        self._assert_parameter(parameter)

        if isinstance(value, str):
            value_cmp = value.lower()
        else:
            value_cmp = value

        config_type = self.store[parameter].get('type')

        if not config_type:
            message = "No config type"

        set_value = None
        message = ''

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
            raise ValueError(f'{parameter}: {message}')

        self.store[parameter]['value'] = set_value

    def get(self, parameter: str):
        self._assert_parameter(parameter)
        return self.store[parameter].get(
            'value', self.store[parameter].get('default'))

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
    def dump(debug=True):
        
        if debug:
            log_obj = log.debug
        else:
            log_obj = log.info

        log_obj(f'{"Parameter":<45} {"Type":<10} {"Value":<10} {"Default":<10} '
                  f'{"Description":<14}')
        log_obj(f'{"---------":<45} {"------":<10} {"------":<10} {"-------":<10} '
                  f'{"-----------------------":<14}')

        for (parameter, description, default, current, datatype) in GlobalConfig.list():
            log_obj(f'{parameter or "":<45} {datatype:<10} {repr(current or ""):<10} '
                      f'{repr(default or ""):<10} {description or "":<14}')


# Setup global application configuration store
GlobalConfig = ConfigStore()

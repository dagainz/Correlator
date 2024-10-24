
import logging
import keyring
from datetime import datetime
from enum import Enum
from functools import cache
from mako.template import Template
from typing import List, Tuple, Dict

log = logging.getLogger(__name__)

DEFAULT_SYSTEM = 'system'
INVALID_FIELDS = {'timestamp', 'summary'}


class EventException(Exception):
    pass


class EventSeverity(Enum):
    Informational = 0
    Warning = 1
    Error = 2

    Default = 0


class Event:

    # Required

    schema: List[Tuple[str, str]] = None
    summary_template: str = None

    # Optional

    severity_override: int = None

    # Internal

    templates = {
        'text/plain': {
            'summary': None
        }
    }

    def __init__(self,
                 payload: Dict[str, str | int | float | None | datetime],  #todo: fix me
                 summary: str = None,
                 severity: int = EventSeverity.Default):

        self._timestamp = datetime.now()
        self._system = DEFAULT_SYSTEM
        if self.severity_override is not None:
            self._severity = self.severity_override
        else:
            self._severity = severity

        self._id = self.__class__.__name__

        self.log = logging.getLogger(self._id)

        if self.schema is None:
            raise EventException(f'{self._id}: Missing schema in class definition')

        # Validate data against schema, and build the data table

        self._data_table = [['Timestamp:', '${timestamp}']]
        self._field_names = ['timestamp']
        self._field_descriptions = {'timestamp': 'Timestamp'}

        payload_copy = payload.copy()
        self._payload = payload.copy()

        missing_fields: List[str] = []
        invalid_fields: List[str] = []

        for field_name, field_description in self.schema:
            self._field_names.append(field_name)
            self._field_descriptions[field_name] = field_description
            if field_name in INVALID_FIELDS:
                invalid_fields.append(field_name)
            elif field_name not in payload:
                missing_fields.append(field_name)
            else:
                self._data_table.append([f'{field_description}:', f'${{{field_name}}}'])
                del payload_copy[field_name]

        messages = []

        if invalid_fields:
            messages.append(f'Payload has invalid field(s): {", ".join(missing_fields)}')

        if missing_fields:
            messages.append(f'Payload has missing field(s): {", ".join(missing_fields)}')

        if len(payload_copy) != 0:
            messages.append(f'Payload has extra field(s): {", ".join(payload_copy.keys())}')

        if messages:
            raise EventException(f'{self._id}: Schema validation failed for the following reason(s): {", ".join(messages)}')

        # Payload ok, resolve all data to strings and numbers

        self._payload = self._resolve_payload(payload)
        self._payload['timestamp'] = self._timestamp

        # Create unique repr

        kv = [f'{field}={self._payload[field]}' for field in self._field_names]
        self._repr = f'{self._id}: ' + ', '.join(kv)

    @staticmethod
    def _resolve_payload(source: dict):
        """Transforms dict values appropriately to use for mako templates.

        Generates and returns a new dict by copying all key and value pairs,
        and transforming the values into either a str, int, or float if they
        aren't already.

        """
        destination = {}

        for key in source:
            if isinstance(source[key], (str, int, float)):
                destination[key] = source[key]
            elif isinstance(source[key], datetime):
                from Correlator.core import format_timestamp
                destination[key] = format_timestamp(source[key])
            elif source[key] is None:
                destination[key] = 'None'
            else:
                raise ValueError(f'Cannot translate type: {type(source[key])}')

        return destination

    @property
    def timestamp(self):
        return self._timestamp

    @property
    def id(self):
        return self._id

    @property
    def fq_id(self):
        return f'{self.system}-{self.id}'

    @property
    def severity(self):
        return self._severity

    @property
    def severity_name(self):
        return EventSeverity(self._severity).name

    @property
    def system(self):
        return self._system

    @system.setter
    def system(self, value):
        self._system = value

    @property
    def summary(self):
        return self.render_summary('text/plain')

    @cache
    def render_summary(self, content_type: str = 'text/plain'):
        templates = self.templates[content_type]
        summary_template = templates.get('summary')
        if summary_template:
            try:
                return Template(summary_template).render(**self._payload)
            except Exception as e:
                message = f'Summary template failed to render: {e}'
                self.log.error(e)
                self.log.exception(e)
                raise EventException(message)
        else:
            return self._repr

    @property
    def field_names(self):
        return self._field_names

    @property
    def field_values(self):
        for field in self.field_names:
            yield self._payload[field]

    @property
    def content_types(self):
        return list(self.templates.keys())

    def __str__(self):
        return self.summary

    def __repr__(self):
        return f'[{self.system} :: {self.id}]: {self.summary}'

    @cache
    def render_datatable(self, content_type='text/plain', **kwargs):
        template = self.create_datatable(content_type, self._data_table, **kwargs)

        return Template(template).render(**self._payload)

    # Legacy mako generation, kept for transitional purposes.

    def create_datatable(self, content_type: str, rows, **kwargs):
        if content_type == 'text/plain':
            text = ''
            for row in rows:
                for cell in row:
                    text += cell + " "
                text += "\n"
            return text
        elif content_type == 'text/html':
            css_class = kwargs.get('css_class', 'datatable')
            header = kwargs.get('header')
            html = f'<table class="{css_class}">'
            if header is not None:
                html += "<tr>"
                for cell in header:
                    html += f"<th>{cell}</th>"
                html += "</tr>"

            for row in rows:
                html += "<tr>"
                for cell in row:
                    html += f"<td>{cell}</td>"
                html += "</tr>"

            html += "</table>"
            return html
        else:
            raise EventException(f'I do not know how to render content type {content_type}')


class StatsEvent(Event):
    pass


class SimpleError(Event):
    schema = [['message', 'Message']]
    summary_template = "Error: ${message}"
    severity_override = EventSeverity.Error


class SimpleWarning(Event):
    schema = [['message', 'Message']]
    summary_template = "Warning: ${message}"
    severity_override = EventSeverity.Error


class SimpleNotice(Event):
    schema = [['message', 'Message']]
    summary_template = "${message}"
    severity_override = EventSeverity.Informational


class EventListener:

    def __init__(self, name: str, filter_template=None, default_action=True):

        self.filter_template = filter_template
        self.default_action = default_action
        self.handler_name = name
        self.log = logging.getLogger(f'{self.handler_name}-handler')
        self.configuration_prefix = f'handler.{self.handler_name}.'

        self.log.debug(f'Initialized base handler')

    def credentials_req(self) -> [str]:
        return []

    def get_creds(self, user_id: str):
        return keyring.get_password('Correlator', f'{self.handler_name}.{user_id}')

    def process_event(self, event: Event):
        raise NotImplementedError

    def initialize(self):
        raise NotImplementedError

    def add_to_config(self, config_item):
        from Correlator.config_store import RuntimeConfig

        RuntimeConfig.add(config_item, 'handler', self.handler_name)

    def get_config(self, key):
        from Correlator.config_store import RuntimeConfig

        return RuntimeConfig.get(self.configuration_prefix + key)


class EventProcessor:

    def __init__(self):
        self.listeners: list[EventListener] = []

    def register_listener(self, event_listener: EventListener):
        self.listeners.append(event_listener)

    def dispatch_event(self, event: Event):
        log.debug(f'Received event {event.id}')
        for listener in self.listeners:
            log.debug(f'Checking if handler {listener.handler_name} is interested')
            wants_to_handle = False
            if listener.filter_template is not None:
                data = {'event': event}
                try:
                    res = listener.filter_template.render(**data)
                    if res == 'True':
                        log.debug('Yes, filter expression evaluated as True')
                        wants_to_handle = True
                    else:
                        log.debug('No, filter expression evaluated as False')
                except Exception as e:
                    log.debug(f'No, filter expression caught exception {e}')
                    log.exception(e)
            else:
                wants_to_handle = listener.default_action
                log.debug(f'Falling through to default action of {wants_to_handle}')
            if wants_to_handle:
                listener.process_event(event)

    def check_creds(self):
        creds = []
        for listener in self.listeners:
            for cred in listener.credentials_req():
                creds.append(f'{listener.handler_name}.{cred}')
        return creds

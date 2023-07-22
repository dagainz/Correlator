import csv as csv_module
import logging
import keyring
from datetime import datetime
from io import StringIO
from mako.template import Template
from typing import List

log = logging.getLogger(__name__)


class EventType:
    """ For future use """
    Standard: int = 0
    Dataset: int = 1


class EventStatus:
    Informational: int = 0
    Warning: int = 1
    Error: int = 2


class Event:
    """Base class for all events.

    This is not meant to be instantiated directly. Modules should use one of the
    subclasses ErrorEvent, WarningEvent, or NoticeEvent, or a custom
    subclass of DataEvent.

    The mako template properties are currently only used by data table support
    in DataSetEvents, but expanded future use is planned.

    Args:
        summary: Summary string
        payload: Optional payload consisting of key/value pairs
        system: String identifier of the originating system

    """

    event_id: str = None
    system_id: str = None
    event_desc: str = None
    field_names: List[str] = None
    data_table: dict = None

    def __init__(self,
                 summary: str,
                 payload: dict = None,
                 system: str = None,
                 status: int = EventStatus.Informational,
                 event_type: int = EventType.Standard):

        self._system_id = self.system_id

        if system is not None:
            self._system_id = system
        else:
            self._system_id = self.system_id

        if self._system_id is None:
            self._system_id = 'Unspecified'

        self._payload: dict = payload

        self._status = status
        self._event_type = event_type
        self._event_id = None
        self._event_desc = None

        # self._is_error: bool = False
        # self._is_warning: bool = False

        self._summary: str = summary
        self._timestamp: datetime = datetime.now()

        self._template_txt: Template | None = None
        self._template_html: Template | None = None

        # Auto generate text and html table using mako templates, if provided.

        if self.data_table is not None:
            self._template_txt = Template(self._text_datatable(self.data_table))
            self._template_html = Template(
                self._html_datatable(self.data_table))

    @property
    def type(self):
        return self._event_type

    def id(self):
        return self._event_type

    @property
    def status(self):
        return self._status

    @property
    def system(self):
        return self._system_id

    @system.setter
    def system(self, value):
        self._system_id = value

    @property
    def summary(self):
        return self._summary

    def __str__(self):
        return self._summary

    def render_text(self):
        if self._payload and self._template_txt:
            return self._template_txt.render(**self._payload)

    def render_html(self):
        if self._payload and self._template_html:
            return self._template_html.render(**self._payload)

    # todo: This doesn't feel right

    def csv_header(self):
        return ''
        # raise NotImplementedError

    def csv_row(self):
        return ''
        # raise NotImplementedError

    @staticmethod
    def _html_datatable(rows, css_class='datatable', header=None):
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

    @staticmethod
    def _text_datatable(rows):
        text = ''
        for row in rows:
            for cell in row:
                text += cell + " "
            text += "\n"
        return text


class DataEvent(Event):
    """Base class for Data Events.

    Data events are events that contain a data structure guaranteed to follow
    a predetermined schema. This schema defines the data to contain:

    - A single collection of key/value pairs. There can be no additional
    nesting.
    - A list containing all the field names (key values). Each event must
    contain a key/value pair in the payload for every field in field name list
    (and no more).

    Since the data schema is set within the class declaration, each
    individual type of event must be defined as a uniquely named python
    class, which subclasses this one.

    These are designed to be simple to define. Setting the following class
    variables in the subclass is almost always enough. Then they may be
    dispatched with a python dictionary as payload, containing all the required
    key/value pairs.

    Data tables are an optional feature of Data Events. It is a facility in
    which an array of 2 position lists get rendered by mako to generate a
    textual and html table representation of the event for use in event
    handlers. The payload from the data event is supplied to mako, so any
    of the keys/value are available to the data table.


    Attributes:

        event_id: **Required** unique identifier for this event.
        event_desc: **Required** Short textual description of the event.
        field_names: **Required:** list of strings that represent the names of
            the fields in the payload. Position dependent handlers (such as CSV)
            will honor the field order defined here
        data_table: **Optional:** list of name, mako expression pairs to use
            when automatically generating text and html representations of the
            payload.
        set_error: Set to True to indicate these events are errors
        set_warning: Set to True to indicate these events are warnings

    """

    # To be defined in subclass

    event_id: str = None
    event_desc: str = None
    field_names: List[str] = None
    data_table: dict = None

    set_error: bool = False
    set_warning: bool = False

    def __init__(self, payload: dict, status: int = None):

        if self.field_names is None:
            raise ValueError('Attribute field_names is not defined in this '
                             'child')

        if self.event_id is None:
            raise ValueError('Attribute event_id is not defined in this child')

        if self.event_desc is None:
            raise ValueError('Attribute event_desc is not defined in this'
                             ' child')
        self._event_id = self.event_id
        self._event_desc = self.event_desc

        # 'timestamp' is mandatory but overridable

        # Ensure it will always be the first field

        self._fields = self.field_names.copy()

        try:
            self._fields.remove('timestamp')
        except ValueError:
            pass

        self._fields = ['timestamp'] + self._fields

        # If it has not been set in the payload, set it to now.

        if 'timestamp' not in payload:
            payload['timestamp'] = datetime.now()

        # Normalize all data in the payload to numbers and strings.

        payload = self._resolve_payload(payload)

        kv = [f'{field}={payload[field]}' for field in self._fields]
        self.repr = f'Data: event_id={self._event_id}, ' + ', '.join(kv)

        # Set status. Let status set in constructor override class level
        # definitions

        if status is None:
            if self.set_error:
                status = EventStatus.Error
            elif self.set_warning:
                status = EventStatus.Warning
            else:
                status = EventStatus.Informational

        super().__init__(self.repr, payload=payload,
                         event_type=EventType.Dataset,
                         status=status)

        # todo: Review

        self.buffer = StringIO()

        self.writer = csv_module.DictWriter(self.buffer, self._fields)

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
                from Correlator.util import format_timestamp
                destination[key] = format_timestamp(source[key])
            elif source[key] is None:
                destination[key] = 'None'
            else:
                raise ValueError(f'Cannot translate type: {type(source[key])}')

        return destination

    def csv_header(self):
        self.writer.writeheader()
        value = self.buffer.getvalue().strip("\r\n")
        self.buffer.seek(0)
        self.buffer.truncate(0)
        return value

    def csv_row(self):
        self.writer.writerow(self._payload)
        value = self.buffer.getvalue().strip("\r\n")
        self.buffer.seek(0)
        self.buffer.truncate(0)
        return value


class ErrorEvent(Event):

    def __init__(self, summary):
        super().__init__(summary, status=EventStatus.Error)


class WarningEvent(Event):

    def __init__(self, summary):
        super().__init__(summary, status=EventStatus.Warning)


class NoticeEvent(Event):
    pass


class EventListener:

    def __init__(self, name: str, filter_template=None, default_action=True):

        self.filter_template = filter_template
        self.default_action = default_action
        self.name = name
        log.debug(f'Initialized listener {self.name}')

    def credentials_req(self) -> [str]:
        return []

    def get_creds(self, user_id: str):
        return keyring.get_password('Correlator', f'{self.name}.{user_id}')

    def process_event(self, event: Event):
        raise NotImplementedError


class EventProcessor:

    def __init__(self):
        self.listeners: list[EventListener] = []

    def register_listener(self, event_listener: EventListener):
        self.listeners.append(event_listener)

    def dispatch_event(self, event: Event):
        log.debug(f'Received event {event.event_id}')
        for listener in self.listeners:
            log.debug(f'Checking if handler {listener.name} is interested')
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
            else:
                wants_to_handle = listener.default_action
                log.debug(f'Falling through to default action of {wants_to_handle}')
            if wants_to_handle:
                listener.process_event(event)

    def check_creds(self):
        creds = []
        for listener in self.listeners:
            for cred in listener.credentials_req():
                creds.append(f'{listener.name}.{cred}')
        return creds

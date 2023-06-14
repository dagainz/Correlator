import csv as csv_module
import logging
import keyring
from datetime import datetime
from io import StringIO
from mako.template import Template
from typing import List

log = logging.getLogger(__name__)


class EventTypes:
    """ For future use """
    Standard: int = 0
    Dataset: int = 1


class Event:
    """Base class for all events.

    This is not meant to be instantiated directly. Modules should use one of the
    subclasses ErrorEvent, WarningEvent, or NoticeEvent, or a custom
    subclass of DataSetEvent.

    The mako template properties are currently only used by data table support
    in DataSetEvents, but expanded future use is planned.

    Attributes:
        is_audit: Audit event?
        is_error: Is error set?
        is_warning: Is warning set?
        summary: Summary string
        timestamp: Event timestamp
        template_txt: Mako template to render text
        template_html: Mako template to render html

    Args:
        summary: Summary string
        payload: Optional payload consisting of key/value pairs
        system: String identifier of the originating system

    """

    audit_id: List[str] = None
    audit_desc: str = None
    field_names: List[str] = None
    data_table = None

    def __init__(self, summary: str, payload: dict | None = None,
                 system: str = 'None'):

        self.system: str = system
        self.payload: dict = payload

        # Notice, by default

        self.is_error: bool = False
        self.is_warning: bool = False

        # Not an audit event
        self.is_audit: bool = False

        self.summary: str = summary
        self.timestamp: datetime = datetime.now()

        self.template_txt: Template | None = None
        self.template_html: Template | None = None

        # Auto generate text and html table mako templates, if provided.

        if self.data_table is not None:
            self.template_txt = Template(self._text_datatable(self.data_table))
            self.template_html = Template(self._html_datatable(self.data_table))

    def __repr__(self):
        prefix = ''
        if self.is_error:
            prefix = 'Error: '
        elif self.is_warning:
            prefix = 'Warning: '

        return prefix + self.summary

    def render_text(self):
        if self.payload and self.template_txt:
            return self.template_txt.render(**self.payload)

    def render_html(self):
        if self.payload and self.template_html:
            return self.template_html.render(**self.payload)

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


class AuditEvent(Event):
    """Base class for Audit Events.

    Audit events are custom classes with this one as its parent. To define an
    audit event that can be dispatched from a module, define a class based on
    this one, and define the following class variables:

    Attributes:

        audit_id: **Required:** unique identifier for this event.
        audit_desc: **Required:** Short textual description of the event.
        field_names: **Required:** list of strings that represent the names of
            the fields in the payload. Position dependent handlers (such as CSV)
            will honor the field order defined here
        data_table: **Optional:** list of name, mako expression pairs to use
            when automatically generating text and html representations of the
            payload.
        status_error: Set to True to indicate these events are errors
        status_warning: Set to True to indicate these events are warnings

    """

    # To be defined in subclass

    audit_id: str = None
    audit_desc: str = None
    field_names: List[str] = None
    data_table: None|dict = None
    status_error: bool = False
    status_warning: bool = False

    def __init__(self, payload: dict, is_error: bool = False,
                 is_warning: bool = False):

        if self.audit_id is None:
            raise ValueError('Undefined audit_id')

        if self.audit_desc is None:
            raise ValueError('Undefined audit_desc')

        if self.field_names is None:
            raise ValueError('Undefined field names')

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

        # CSV module requires strings or numbers. Resolve any other types

        payload = self._resolve_payload(payload)

        # Simple repr, at least for now.
        # todo: Review

        kv = [f'{field}={payload[field]}' for field in self._fields]
        self.repr = self.audit_id + ': ' + ', '.join(kv)

        super().__init__(self.repr, payload=payload)
        self.is_audit = True

        # Set error or warning flags

        # default to using class variables

        self.is_error: bool = self.status_error
        self.is_warning: bool = self.status_warning

        # Allow constructor overrides

        if is_error:
            self.is_error = True
        if is_warning:
            self.is_warning = True

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
        self.writer.writerow(self.payload)
        value = self.buffer.getvalue().strip("\r\n")
        self.buffer.seek(0)
        self.buffer.truncate(0)
        return value


class ErrorEvent(Event):

    def __init__(self, summary, **kwargs):
        super().__init__(summary, **kwargs)
        self.is_error = True


class WarningEvent(Event):

    def __init__(self, summary, **kwargs):
        super().__init__(summary, **kwargs)
        self.is_warning = True


class NoticeEvent(Event):
    pass


class EventListener:

    name = 'Unknown'

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
        for listener in self.listeners:
            listener.process_event(event)

    def check_creds(self):
        creds = []
        for listener in self.listeners:
            for cred in listener.credentials_req():
                creds.append(f'{listener.name}.{cred}')
        return creds

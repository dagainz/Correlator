import csv as csv_module
import logging
import keyring
from datetime import datetime
from io import StringIO
from mako.template import Template

log = logging.getLogger(__name__)


class Event:
    def __init__(self, summary, **kwargs):
        # todo: Review arg usage

        self.system = kwargs.get('system', 'None')
        self.record = kwargs.get('record', None)
        self.payload = kwargs.get('payload', None)
        self.table_data = kwargs.get('table_data', None)

        self.is_error = False
        self.is_warning = False
        self.is_audit = False

        self.audit_id = None
        self.audit_desc = None

        self.summary = summary
        self.timestamp = datetime.now()

        # Auto generate text and html tables

        if self.table_data is not None:
            self.template_txt = Template(self.text_datatable(self.table_data))
            self.template_html = Template(self.html_datatable(self.table_data))
        else:
            self.template_txt = None
            self.template_html = None

    def __repr__(self):
        raise NotImplementedError

    def render_text(self):
        if self.payload and self.template_txt:
            return self.template_txt.render(**self.payload)

    def render_html(self):
        if self.payload and self.template_html:
            return self.template_html.render(**self.payload)

    def csv_header(self):
        return ''

    def csv_row(self):
        return ''

    @staticmethod
    def html_datatable(rows, cssclass='datatable', header=None):
        html = f'<table class="{cssclass}">'
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
    def text_datatable(rows):
        text = ''
        for row in rows:
            for cell in row:
                text += cell + " "
            text += "\n"
        return text


class AuditEvent(Event):

    fields = []

    def __init__(self, audit_id, payload, table_data):

        # 'timestamp' is mandatory but overridable

        # Ensure it will always be the first field

        self._fields = self.fields.copy()

        try:
            self._fields.remove('timestamp')
        except ValueError:
            pass

        self._fields = ['timestamp'] + self.fields

        # If it has not been set in the payload, set it to now.

        if 'timestamp' not in payload:
            payload['timestamp'] = datetime.now()

        # CSV module requires strings or numbers. Resolve any other types

        payload = self._resolve_payload(payload)

        kv = [f'{field}={payload[field]}' for field in self._fields]
        self.repr = audit_id + ': ' + ', '.join(kv)

        super().__init__(self.repr, payload=payload, table_data=table_data)
        self.is_audit = True
        self.audit_id = audit_id
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

    def __repr__(self):
        return self.repr

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

    def __repr__(self):
        return f'ERROR: {self.timestamp}: {self.summary}'


class WarningEvent(Event):

    def __init__(self, summary, **kwargs):
        super().__init__(summary, **kwargs)
        self.is_warning = True

    def __repr__(self):
        return f'WARNING: {self.timestamp}: {self.summary}'


class NoticeEvent(Event):

    def __repr__(self):
        return f'NOTICE: {self.timestamp}: {self.summary}'


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

import csv
import logging
from datetime import datetime
from io import StringIO

log = logging.getLogger(__name__)


class Event:
    def __init__(self, summary, **kwargs):

        self.system = kwargs.get('system', 'None')
        self.record = kwargs.get('record', None)
        self.data = kwargs.get('data', None)

        self.is_error = False
        self.is_warning = False
        self.is_audit = False

        self.template_txt = None
        self.template_html = None
        self.audit_id = None

        self.summary = summary
        self.datetime_obj = datetime.now()
        self.timestamp = self.datetime_obj.strftime('%Y-%m-%d %H:%M:%S')

    def __repr__(self):
        raise NotImplementedError

    def render_text(self):
        if self.data and self.template_txt:
            return self.template_txt.render(**self.data)

    def render_html(self):
        if self.data and self.template_html:
            return self.template_html.render(**self.data)

    def csv_header(self):
        return ''

    def csv_row(self):
        return ''


class AuditEvent(Event):

    fields = []

    def __init__(self, audit_id, data):
        kv = [f'{field}={data[field]}' for field in self.fields]
        self.repr = 'Audit: ' + ', '.join(kv)

        super().__init__(self.repr, data=data)
        self.is_audit = True
        self.audit_id = audit_id
        self.buffer = StringIO()
        self.writer = csv.DictWriter(self.buffer, self.fields)

    def __repr__(self):
        return self.repr

    def csv_header(self):
        self.writer.writeheader()
        value = self.buffer.getvalue().strip("\r\n")
        self.buffer.seek(0)
        self.buffer.truncate(0)
        return value

    def csv_row(self):
        self.writer.writerow(self.data)
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



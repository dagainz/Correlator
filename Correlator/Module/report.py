import logging
from mako.template import Template

from Correlator.util import Module, format_timestamp, calculate_summary
from Correlator.event import NoticeEvent, AuditEvent, EventProcessor

log = logging.getLogger(__name__)


class ReportStatsEvent(AuditEvent):

    audit_id = 'module-stats'
    fields = ['start', 'end', 'duration', 'messages', 'size']

    def __init__(self, data):
        super().__init__(self.audit_id, data)

        self.template_txt = Template(
            'Syslog record reporting started at ${start} and ended at ${end} '
            'for a duration of ${duration}. ${messages} total messages '
            '(${size} bytes) were processed.')


class Report(Module):

    def __init__(self, processor: EventProcessor):

        self.processor = processor
        self.description = 'Report-only'
        self.identifier = 'Report'
        self.module_name = self.identifier

        self.num_records = 0
        self.size_records = 0
        self.start = None
        self.end = None

    def statistics(self, reset=False):

        data = {
            'start': format_timestamp(self.start),
            'end': format_timestamp(self.end),
            'duration': self._calculate_duration(self.start, self.end),
            'messages': self.num_records,
            'size': self.size_records
        }

        self.dispatch_event(ReportStatsEvent(data))

        if reset:
            self.num_records = 0
            self.size_records = 0
            self.start = None
            self.end = None

    def process_record(self, record):
        recordsize = len(record)

        if self.start is None or record.timestamp < self.start:
            self.start = record.timestamp

        if self.end is None or record.timestamp > self.end:
            self.end = record.timestamp

        self.dispatch_event(
            NoticeEvent(
                calculate_summary(str(record)), record=record))

        self.num_records += 1
        self.size_records += recordsize

        return True

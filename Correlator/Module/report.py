import logging
from dataclasses import dataclass
from datetime import datetime
from mako.template import Template

from Correlator.util import Module, format_timestamp, calculate_summary
from Correlator.Event.core import NoticeEvent, AuditEvent

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


@dataclass
class ReportState:
    start: datetime = None
    end: datetime = None
    num_records: int = 0
    size_records: int = 0


class Report(Module):

    def __init__(self):

        super().__init__()

        self.description = 'Report-only'
        self.identifier = 'Report'
        self.module_name = self.identifier
        self.model = ReportState

    def _clear_stats(self):
        log.debug('Clear Stats')
        self.state.num_records = 0
        self.state.size_records = 0
        self.state.start = None
        self.state.end = None

    def statistics(self, reset=False):

        data = {
            'start': format_timestamp(self.state.start),
            'end': format_timestamp(self.state.end),
            'duration': self._calculate_duration(
                self.state.start, self.state.end),
            'messages': self.state.num_records,
            'size': self.state.size_records,
            'reset': reset
        }

        self.dispatch_event(ReportStatsEvent(data))

        if reset:
            self._clear_stats()

    def process_record(self, record):

        recordsize = len(record)

        if self.state.start is None or record.timestamp < self.state.start:
            self.state.start = record.timestamp

        if self.state.end is None or record.timestamp > self.state.end:
            self.state.end = record.timestamp

        self.dispatch_event(
            NoticeEvent(
                calculate_summary(str(record)), record=record))

        self.state.num_records += 1
        self.state.size_records += recordsize

        return True


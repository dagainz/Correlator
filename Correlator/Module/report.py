import logging
from dataclasses import dataclass
from datetime import datetime

from Correlator.util import Module, format_timestamp, calculate_summary
from Correlator.Event.core import NoticeEvent, AuditEvent

log = logging.getLogger(__name__)


class ReportStatsEvent(AuditEvent):

    audit_id = 'module-stats'
    fields = ['start', 'end', 'duration', 'messages', 'size']

    def __init__(self, data):

        table = [
                ['Session start:', '${start}'],
                ['Session end:', '${end}'],
                ['Session duration:', '${duration}'],
                ['Number of log records:', '${messages}'],
                ['Total size (bytes):', '${size}']
            ]

        super().__init__(self.audit_id, data, table_data=table)

        self.audit_desc = 'Statistics for the report-only module'


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
        self.store.num_records = 0
        self.store.size_records = 0
        self.store.start = None
        self.store.end = None

    def statistics(self, reset=False):

        data = {
            'start': format_timestamp(self.store.start),
            'end': format_timestamp(self.store.end),
            'duration': self._calculate_duration(
                self.store.start, self.store.end),
            'messages': self.store.num_records,
            'size': self.store.size_records,
        }

        self.dispatch_event(ReportStatsEvent(data))

        if reset:
            self._clear_stats()

    def process_record(self, record):

        recordsize = len(record)

        if self.store.start is None or record.timestamp < self.store.start:
            self.store.start = record.timestamp

        if self.store.end is None or record.timestamp > self.store.end:
            self.store.end = record.timestamp

        self.dispatch_event(
            NoticeEvent(
                calculate_summary(str(record)), record=record))

        self.store.num_records += 1
        self.store.size_records += recordsize

        return True

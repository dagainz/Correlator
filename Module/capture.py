from datetime import datetime, timedelta
from common.util import Module
from common.event import NoticeEvent, EventProcessor


class CaptureOnly(Module):

    def __init__(self, processor: EventProcessor, log):

        self.log = log
        self.processor = processor
        self.description = 'Syslog Capture support'
        self.identifier = 'Capture'

        self.module_name = self.identifier

        self.states = {}
        self.num_records = 0
        self.size_records = 0
        self.start = None
        self.end = None

    def statistics(self):

        messages = [
            'Capture started at {}'.format(self.start),
            'Capture ended at {}'.format(self.end),
            'Capture duration: {}'.format(str(self.end - self.start)),
            '{} total syslog messages captured'.format(
                self.num_records),
            '{} total bytes of syslog messages captured'.format(
                self.size_records)

        ]

        return messages

    def process_record(self, record):
        recordsize = len(record)

        if self.start is None or record.timestamp < self.start:
            self.start = record.timestamp

        if self.end is None or record.timestamp > self.end:
            self.end = record.timestamp

        summary = '{} byte record captured'.format(recordsize)
        self.dispatch_event(NoticeEvent(summary, record))
        self.num_records += 1
        self.size_records += recordsize

        return True



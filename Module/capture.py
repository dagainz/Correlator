from datetime import datetime, timedelta

"""This module reports on i280 activity through the Message Queue"""
from Notify.notify import Notification


class CaptureOnly:

    def __init__(self, notifier, log):

        self.states = {}
        self.log = log
        self.notifier = notifier
        self.description = 'Assistance with raw syslog record capturing'
        self.identifier = 'CaptureHelper'

        self.num_records = 0
        self.size_records = 0
        self.start = None
        self.end = None

    def log_statistics(self):

        self.log.info(
            'Capture started at {}'.format(self.start)),  3
        self.log.info(
            'Capture ended at {}'.format(self.end))
        self.log.info(
            'Capture duration: {}'.format(str(self.end - self.start)))
        self.log.info(
            '{} total syslog messages captured'.format(
                self.num_records))
        self.log.info(
            '{} total bytes of syslog messages captured'.format(
                self.size_records))

    def process_record(self, record):
        recordsize = len(record)

        if self.start is None or record.timestamp < self.start:
            self.start = record.timestamp

        if self.end is None or record.timestamp > self.end:
            self.end = record.timestamp

        self.notifier.notice(Notification(
            '{} byte record captured'.format(recordsize)), record)
        self.num_records += 1
        self.size_records += recordsize

        return True



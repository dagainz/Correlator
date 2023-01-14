from datetime import datetime, timedelta

"""This module reports on activity """

from notify import Notification


class Report:

    def __init__(self, notifier, log):

        self.log = log
        self.notifier = notifier
        self.description = 'Module that reports on syslog activity'
        self.identifier = 'Report'

        self.num_records = 0
        self.size_records = 0
        self.start = None
        self.end = None

    def statistics(self):

        return []

        # self.notifier.send_info(
        #     'Capture started at {}'.format(self.start))
        # self.notifier.send_info(
        #     'Capture ended at {}'.format(self.end))
        # self.notifier.send_info(
        #     'Capture duration: {}'.format(str(self.end - self.start)))
        # self.notifier.send_info(
        #     '{} total syslog messages captured'.format(
        #         self.num_records))
        # self.notifier.send_info(
        #     '{} total bytes of syslog messages captured'.format(
        #         self.size_records))

    def process_record(self, record):
        recordsize = len(record)

        if self.start is None or record.timestamp < self.start:
            self.start = record.timestamp

        if self.end is None or record.timestamp > self.end:
            self.end = record.timestamp

        self.notifier.notice(Notification(
            '{} {} {} {}'.format(
                record.hostname, record.appname, record.prog,
                record.detail[0:20]), record))
        self.num_records += 1
        self.size_records += recordsize

        return True



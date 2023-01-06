import csv
import os
from datetime import datetime
from typing import List, Any

from lib.util import rotate_file


class Notification:
    def __init__(self, message: str, record, detail=None):

        if detail is None:
            detail = {}

        self.message = message
        self.detail = detail
        self.record = record


class Notify:
    def __init__(self, **kwargs):
        """
        Defaults are all True. If otherwise, can use:
        do_warn = False
        do_notice = False
        do_error = False
        do_audit = False
        do_debug = False

        """

        self.args = kwargs

    def warn(self, notif: Notification):
        if self.args.get('do_warn'):
            self.handle_warn(notif)

    def error(self, notif: Notification):
        if self.args.get('do_error'):
            self.handle_error(notif)

    def notice(self, notif: Notification):
        if self.args.get('do_notice'):
            self.handle_notice(notif)

    def debug(self, notif: Notification):
        if self.args.get('do_debug'):
            self.handle_debug(notif)

    def audit(self, notif: Notification):
        if self.args.get('do_audit'):
            self.handle_audit(notif)

    def handle_warn(self, notif: Notification):
        raise NotImplementedError

    def handle_error(self, notif: Notification):
        raise NotImplementedError

    def handle_notice(self, notif: Notification):
        raise NotImplementedError

    def handle_debug(self, notif: Notification):
        raise NotImplementedError

    def handle_audit(self, notif: Notification):
        raise NotImplementedError


class Notifiers:

    notifiers: list[Notify]

    def __init__(self):
        self.notifiers = []

    # Not type safe
    def add_notifier(self, notifier):
        self.notifiers.append(notifier)

    def warn(self, notif: Notification):
        for notifier in self.notifiers:
            notifier.warn(notif)

    def error(self, notif: Notification):
        for notifier in self.notifiers:
            notifier.error(notif)

    def notice(self, notif: Notification):
        for notifier in self.notifiers:
            notifier.notice(notif)

    def audit(self, notif: Notification):
        for notifier in self.notifiers:
            notifier.audit(notif)

    def debug(self, notif: Notification):
        for notifier in self.notifiers:
            notifier.debug(notif)


class CSVNotify(Notify):
    """Creates a notifier that ignores everything but audit events.

    Sends output to a csv file called [module identifier]-audit.csv

    Rotate and prune existing logs, keeping ROTATE_KEEP revisions

    """

    ROTATE_KEEP = 10

    def __init__(self):
        super().__init__()
        self.initialized_files = {}

    def initialize_module(self, module):

        csv_basename = '{}-audit'.format(module)

        rotate_file(csv_basename, 'csv')
        # # Check if the csv file exists, and if so, rotates old logs
        # # and then renames the existing file to .1
        #
        # if os.path.exists(csv_basename + '.csv'):
        #     for number in range(self.ROTATE_KEEP - 1, 0, -1):
        #         old_name = csv_basename + "_" + str(number) + ".csv"
        #         if os.path.exists(old_name):
        #             new_name = csv_basename + "_" + str(number + 1) + ".csv"
        #             os.rename(old_name, new_name)
        #     old_name = csv_basename + '.csv'
        #     new_name = csv_basename + "_1.csv"
        #     os.rename(old_name, new_name)
        #     # csv_filename is now clear

        file_obj = open(csv_basename + '.csv', 'w', newline='')
        self.initialized_files[module] = file_obj

    def audit(self, notif: Notification):
        # was send_audit(self, module, data, headers=None):
        # if module not in self.initialized_files:
        #     self.initialize_module(module)
        #
        # file_obj = self.initialized_files[module]
        # if not isinstance(data, dict):
        #     data = {
        #         'Timestamp': datetime.now(),
        #         'Message': data
        #     }
        #     headers = ['Timestamp', 'Message']
        # else:
        #     if not headers:
        #         headers = list(data.keys())
        # writer = csv.DictWriter(file_obj, fieldnames=headers)
        # fppos = file_obj.tell()
        # if fppos == 0:
        #     writer.writeheader()
        # writer.writerow(data)

        pass


# class ConsoleNotify(Notify):
#     """Simple notifier to display to console.
#
#     For now, ignores any audit events
#
#     """
#
#     def warn(self, message):
#         print("CON-NOTIFY(WARNING): {}".format(message))
#
#     def send_info(self, message):
#         print("CON-NOTIFY(INFO): {}".format(message))
#
#     def send_crit(self, message):
#         print("CON-NOTIFY(CRITICAL): {}".format(message))
#
#     def send_error(self, message):
#         print("CON-NOTIFY(ERROR): {}".format(message))
#
#     def send_audit(self, message, headers):
#         # don't handle, for now.
#         return


class LogbackNotify(Notify):
    """Simple notifier to report on records captured.
    """

    def __init__(self, log, prefix=None):
        super().__init__()
        self.log = log
        self.prefix = ''
        if prefix:
            self.prefix = prefix + ': '

    def handle_warn(self, notif: Notification):
        self.log.warning(self.prefix + notif.message)

    def handle_notice(self, notif: Notification):
        self.log.info(self.prefix + notif.message)

    def handle_error(self, notif: Notification):
        self.log.error(self.prefix + notif.message)

    def handle_audit(self, notif: Notification):
        # Don't handle
        return

    def handle_debug(self, notif: Notification):
        self.log.debug(self.prefix + notif.message)

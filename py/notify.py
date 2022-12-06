import csv
import os
from datetime import datetime


class Notify:
    def send_warning(self, message):
        raise NotImplementedError

    def send_info(self, message):
        raise NotImplementedError

    def send_error(self, message):
        raise NotImplementedError

    def send_crit(self, message):
        raise NotImplementedError

    def send_audit(self, message, headers):
        raise NotImplementedError


class Notifiers:
    def __init__(self, notifiers=None):
        if notifiers is not None:
            self.notifiers = notifiers
        else:
            self.notifiers = []

    # Not type safe
    def add_notifier(self, notifier):
        self.notifiers.append(notifier)

    def send_warning(self, message):
        for notifier in self.notifiers:
            notifier.send_warning(message)

    def send_error(self, message):
        for notifier in self.notifiers:
            notifier.send_error(message)

    def send_info(self, message):
        for notifier in self.notifiers:
            notifier.send_info(message)

    def send_crit(self, message):
        for notifier in self.notifiers:
            notifier.send_crit(message)

    def send_audit(self, message, headers=None):
        for notifier in self.notifiers:
            notifier.send_audit(message, headers)


class CSVNotify(Notify):
    """Creates a notifier that ignores everything but audit events.

    Sends output to a csf file called [module identifier]-audit.csv

    Rotate and prune existing logs, keeping ROTATE_KEEP revisions

    """
    ROTATE_KEEP = 10

    def __init__(self):
        self.initialized_files = {}

    def initialize_module(self, module):
        csv_filename = '{}-audit.csv'.format(module)

        # Check if the csv file exists, and if so, rotates old logs
        # and then renames the existing file to .1

        if os.path.exists(csv_filename):
            for number in range(self.ROTATE_KEEP - 1, 0, -1):
                old_name = csv_filename + "." + str(number)
                if os.path.exists(old_name):
                    new_name = csv_filename + "." + str(number + 1)
                    os.rename(old_name, new_name)
            old_name = csv_filename
            new_name = csv_filename + ".1"
            os.rename(old_name, new_name)
            # csv_filename is now clear

        file_obj = open(csv_filename, "w", newline='')
        self.initialized_files[module] = file_obj

    def send_warning(self, message):
        return

    def send_info(self, message):
        return

    def send_crit(self, message):
        return

    def send_error(self, message):
        return

    def send_audit(self, module, data, headers=None):
        if module not in self.initialized_files:
            self.initialize_module(module)

        file_obj = self.initialized_files[module]
        if not isinstance(data, dict):
            data = {
                'Timestamp': datetime.now(),
                'Message': data
            }
            headers = ['Timestamp', 'Message']
        else:
            if not headers:
                headers = list(data.keys())
        writer = csv.DictWriter(file_obj, fieldnames=headers)
        fppos = file_obj.tell()
        if fppos == 0:
            writer.writeheader()
        writer.writerow(data)


class ConsoleNotify(Notify):
    """Simple notifier to display to console.

    For now, ignores any audit events

    """

    def send_warning(self, message):
        print("CON-NOTIFY(WARNING): {}".format(message))

    def send_info(self, message):
        print("CON-NOTIFY(INFO): {}".format(message))

    def send_crit(self, message):
        print("CON-NOTIFY(CRITICAL): {}".format(message))

    def send_error(self, message):
        print("CON-NOTIFY(ERROR): {}".format(message))

    def send_audit(self, message, headers):
        # don't handle, for now.
        return


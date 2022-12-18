from datetime import datetime
import logging
import os
import sys

DEFAULT_ROTATE_KEEP=10

class ParserError(Exception):
    pass


class LogHelper:

    @staticmethod
    def initialize_console_logging(log, log_level):
        ch = logging.StreamHandler(sys.stdout)

        ch.setLevel(log_level)
        log.setLevel(log_level)

        formatter = logging.Formatter(
            '%(asctime)s: %(levelname)s: %(message)s',
            '%Y-%m-%d %H:%M:%S')

        ch.setFormatter(formatter)
        log.addHandler(ch)


def build_modules(modules, notifiers, log):
    moduledict = {}
    for module in modules:
        obj = module(notifiers, log)
        moduledict[obj.identifier] = obj
    return moduledict


def rotate_file(basename, ext, keep = DEFAULT_ROTATE_KEEP):

    # Check if the file exists, and if so, rotates old files
    # and then renames the existing file to add _1 before the
    # extension

    if os.path.exists(basename + '.' + ext):
        for number in range(keep - 1, 0, -1):
            old_name = basename + "_" + str(number) + '.' + ext
            if os.path.exists(old_name):
                new_name = basename + "_" + str(number + 1) + '.' + ext
                os.rename(old_name, new_name)
        old_name = basename + '.' + ext
        new_name = basename + '_1.' + ext
        os.rename(old_name, new_name)
        # csv_filename is now clear


def capture_filename():
    now = datetime.now()
    base_name = now.strftime('%Y%m%d')
    rotate_file(base_name, 'cap')
    return base_name + ".cap"


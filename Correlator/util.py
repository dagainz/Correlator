import logging
import os
import sys
from datetime import datetime

from Correlator.event import Event, EventProcessor

DEFAULT_ROTATE_KEEP = 10
MAX_SUMMARY = 128
MAX_BREAK_SEARCH = 10


class Config:
    def __init__(self):
        self.store = {}

    def get(self, key, default=None):
        return self.store.get(key, default)

    def set(self, key, value):
        self.store[key] = value

    def validate(self, key):
        if isinstance(key, list):
            keys = key
        else:
            keys = [key]

        for key in keys:
            if key not in self.store:
                return False

        return True


GlobalConfig = Config()


class ParserError(Exception):
    pass


def setup_root_logger(log_level):
    logger = logging.getLogger()
    logger.setLevel(log_level)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(log_level)

    # noinspection SpellCheckingInspection
    formatter = logging.Formatter(
        '%(asctime)s %(module)s %(levelname)s: %(message)s', '%Y-%m-%d %H:%M:%S')
    ch.setFormatter(formatter)

    logger.addHandler(ch)

    return logger


class Module:

    module_name = 'System'
    processor: EventProcessor = None
    description: str = ''

    def dispatch_event(self, event: Event):

        if not self.processor:
            raise NotImplemented

        event.system = self.module_name
        self.processor.dispatch_event(event)

    def process_record(self, record):
        raise NotImplemented

    def statistics(self):
        raise NotImplemented

    @staticmethod
    def _calculate_duration(start, end):
        try:
            return str(end - start)
        except TypeError:
            return None


def rotate_file(basename, ext, keep=DEFAULT_ROTATE_KEEP):

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


def capture_filename():
    now = datetime.now()
    base_name = now.strftime('%Y%m%d')
    rotate_file(base_name, 'cap')
    return base_name + ".cap"


def format_timestamp(date: datetime):
    if date:
        return date.strftime('%Y-%m-%d %H:%M:%S')


def calculate_summary(detail: str):
    """Generates a summary line from a string

    Returns the provided string, trimmed to a maximum of MAX_SUMMARY.
    It attempts to do it by using a word boundary if one exists within the
    last MAX_BREAK_SEARCH Characters, otherwise returns exactly MAX_SUMMARY
    characters.

    """

    # the string is smaller than the max length, return it
    if len(detail) <= MAX_SUMMARY:
        return detail

    # Word boundary: If the character directly after the last allowable
    # character by length is a space, then return the entire string left of it.

    if detail[MAX_SUMMARY] == ' ':
        return detail[0:MAX_SUMMARY]

    # if a word boundary is found in the last MAX_BREAK_SEARCH characters,
    # use it to trim the string.

    first = MAX_SUMMARY-1
    last = first - MAX_BREAK_SEARCH
    if last < 0:
        last = 0

    for i in range(first, last, -1):
        if detail[i] == ' ':
            return detail[0:i+1]

    # No boundary found, simply return the max size

    return detail[0:MAX_SUMMARY]

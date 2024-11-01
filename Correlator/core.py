import argparse
import logging
import os
import re
import sys
from datetime import datetime, timedelta
from enum import Enum, IntEnum

import keyring

from Correlator.Event.core import Event
from Correlator.config_store import RuntimeConfig

DEFAULT_ROTATE_KEEP = 10
MAX_SUMMARY = 128
MAX_BREAK_SEARCH = 10

log = logging.getLogger(__name__)


class RecordTypes(IntEnum):
    HEARTBEAT = 0
    SYSLOG_DATA = 1


class ResultCodes(Enum):
    OK = 0
    Error = 1


class Instance:
    Version = os.environ.get("CORRELATOR_VERSION", '0.0.4')


class ParserError(Exception):
    pass


def setup_root_logger(log_level):
    logger = logging.getLogger()
    logger.setLevel(log_level)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(log_level)

    # noinspection SpellCheckingInspection
    formatter = logging.Formatter(
        '%(asctime)s %(name)s %(levelname)s: %(message)s',
        '%Y-%m-%d %H:%M:%S')
    ch.setFormatter(formatter)

    logger.addHandler(ch)

    return logger


def setup_keyring():

    keyring_pass = os.getenv('KEYRING_CRYPTFILE_PASSWORD')
    if keyring_pass:
        from keyrings.cryptfile.cryptfile import CryptFileKeyring
        kr = CryptFileKeyring()
        kr.keyring_key = keyring_pass
        keyring.set_keyring(kr)


class SimpleException(Exception):
    pass


class CredentialsReq(Exception):
    def __init__(self, ids: list[str]):
        self.ids = ids
        super().__init__(', '.join(self.ids))


class Module:

    description: str = ''

    def __init__(self, module_name):
        self._processor = None
        self._store = None
        self.model = None
        self.module_name = module_name
        self.log = logging.getLogger(f'{module_name}-module')
        self.configuration_prefix = f'module.{self.module_name}.'

    @property
    def event_processor(self):
        return self._processor

    @event_processor.setter
    def event_processor(self, value):
        self._processor = value

    @property
    def store(self):
        return self._store

    @store.setter
    def store(self, value):
        self._store = value

    def dispatch_event(self, event: Event):

        self.log.info(f'Dispatching severity {event.severity_name} event {event.id} (fqid: {event.fq_id})')

    def post_init_store(self):
        return

    def handle_record(self, record):
        if self._store is None:
            raise ValueError('No Store!')
        self.process_record(record)

    def process_record(self, record):
        raise NotImplementedError

    def statistics(self):
        raise NotImplementedError

    def initialize(self):
        raise NotImplementedError

    def add_config(self, config_item):
        RuntimeConfig.add(config_item, 'module', self.module_name)

    def get_config(self, key):
        # from Correlator.config import GlobalConfig

        return RuntimeConfig.get(self.configuration_prefix + key)

    @staticmethod
    def _calculate_duration(start, end):
        try:
            return str(end - start)
        except TypeError:
            return None


def listize(item):
    if isinstance(item, list):
        return item

    return [item]


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


def template_dir():
    return os.path.join(
        os.path.dirname(__file__),
        'Templates')


def prefix_run_dir(file_name: str):
    """Prefix the system run directory to a filename if it has no path component

    """
    if not os.path.dirname(file_name):
        run_dir = RuntimeConfig.get('system.run_dir')
        # No path component, filename only
        return os.path.join(run_dir, file_name)
    return file_name


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

    # todo: .rfind()

    for i in range(first, last, -1):
        if detail[i] == ' ':
            return detail[0:i+1]

    # No boundary found, return the max size

    return detail[0:MAX_SUMMARY]


class CountOverTime:
    def __init__(self, expiry_seconds: int, store: dict):
        self.expiry_seconds = expiry_seconds
        self.store = store

    def add(self, identifier, timestamp):
        if identifier not in self.store:
            self.store[identifier] = [timestamp]
            return 1

        earliest = datetime.now() - timedelta(seconds=self.expiry_seconds)
        new_store = [x for x in self.store[identifier] if x >= earliest]
        now = datetime.now()
        if now > earliest:
            new_store.append(now)

        self.store[identifier] = new_store

        return len(new_store)

    def clear(self, identifier: str):
        if identifier in self.store:
            del self.store[identifier]


def process_cmdline_options(cmd_args: argparse.Namespace):
    """Returns a list of list(key,value) options made from an argparse namespace

    arguments in the form --o name=value will be recognized and added.

    """

    res = []
    if cmd_args.o:
        for entry in cmd_args.o:
            m = re.match(r'(.+)=(.+)', entry)
            if m:
                (key, value) = (m.group(1), m.group(2))
                res.append([key, value])

    return res


class ConfigException(Exception):
    pass

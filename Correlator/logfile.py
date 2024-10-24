import logging
import re

from Correlator.Event.core import (EventProcessor, StatsEvent)
from Correlator.core import ParserError, Module, format_timestamp

log = logging.getLogger(__name__)


class LogError(Exception):
    pass


class LogfileStatsEvent(StatsEvent):

    schema = [
        ['start', 'Session started:'],
        ['end', 'Session ended:'],
        ['duration', 'Session duration:'],
    ]
    templates = {
        'text/plain': {
            'summary': 'Log processing session started at ${start}, ended at ${end}, with a duration of ${duration}'
        },
        'text/html': {
            'summary': 'Log processing session started at <strong>${start}</strong>, ended at <strong>${end}</strong>, with a duration of <strong>${duration}</strong>'
        }

    }


class LogRecord:

    """ Base class for custom logfile parser classes to extend

    Args:
        record: Raw record from logfile

    """

    main_regex = None
    """ For simple parsers, just setting this property is enough"""

    def __init__(self, record):

        if self.main_regex is None:
            raise NotImplementedError

        m = re.match(self.main_regex, record)
        if not m:
            raise ParserError('Invalid logfile format')

        self.record = record
        self.match = m

    def __len__(self):
        return len(self.record)


class RecordResult:
    def __init__(self, record, log_record):

        try:
            parsed_record = log_record(record)
            self.record = parsed_record
            self.is_error = False
            self.message = None

        except ParserError as e:
            self.record = None
            self.is_error = True
            self.message = str(e)


class LogfileProcessor:

    """ Read and process records from a log file

    Args:
        log_record: Custom parser class
        modules: List of Correlator modules in this stack
        processor: Instance of EventProcessor with registered event handlers

    """

    def __init__(self, log_record, modules: list[Module],
                 processor: EventProcessor):

        self.start = None
        self.end = None

        self.modules = modules
        self.log_record = log_record

        # No persistence with logfiles

        self.full_store = {}

        for module in modules:
            module.event_processor = processor
            if module.module_name not in self.full_store:
                self.full_store[module.module_name] = module.model()
            module.store = self.full_store[module.module_name]
            module.post_init_store()

    def logfile_reader(self, file_object):
        record = ''
        eof = False
        while not eof:
            line = file_object.readline()
            if line == '':
                data = record
                eof = True
                if data:
                    yield RecordResult(data, self.log_record)

            line = line.rstrip()
            # todo outsource to vendor code
            if line and line[0] == '\x18':
                data = record
                record = line[1:]
                if data:
                    yield RecordResult(data, self.log_record)
            else:
                record += line + '\n'
                # ''{}\n'.format(line)

    def from_file(self, filename):
        with open(filename) as logfile:
            for result in self.logfile_reader(logfile):
                if result.is_error:
                    log.error(f'Error reading entry: {result.message}')
                else:
                    if (self.start is None or
                            result.record.timestamp < self.start):
                        self.start = result.record.timestamp

                    if (self.end is None or
                            result.record.timestamp > self.end):
                        self.end = result.record.timestamp

                    for module in list(self.modules):
                        module.process_record(result.record)

    def log_stats(self, processor: EventProcessor):
        for module in self.modules:
            module.statistics()

        if self.start and self.end:
            duration = (str(self.end - self.start))
        else:
            duration = ''

        e = LogfileStatsEvent(
            {
                'start': format_timestamp(self.start),
                'end': format_timestamp(self.end),
                'duration': duration
            })
        e.system = 'logfile-processor'
        processor.dispatch_event(e)

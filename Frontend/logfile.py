import re
from datetime import datetime
from lib.util import ParserError


class LogRecord:
    """Representation of a logfile record."""

    main_regex = r'(.{28}) (.+?) \[(.*?)\] (.*?) \[(.+?)\] (.+?): (.+)'

    def __init__(self, record):
        """Parses the text record, raises a ParserError if it gets confused"""

        m = re.match(self.main_regex, record)
        if not m:
            raise ParserError('Invalid logfile format')

        # Keep original record
        self.record = record

        # Timestamp str and datetime

        self.str_timestamp = m.group(1)
        self.timestamp = datetime.strptime(self.str_timestamp[0:23],
                                           '%Y-%m-%d %H:%M:%S.%f')
        self.who = m.group(2)
        self.request = m.group(3)
        self.prog = m.group(4)
        self.identifier = m.group(5)
        self.severity = m.group(6)
        self.detail = m.group(7)

    def __repr__(self):
        return "{} {} [{}] {} [{}] {}: {}".format(
            self.str_timestamp, self.who, self.request, self.prog,
            self.identifier, self.severity, self.detail)


class RecordResult:
    def __init__(self, record):

        try:
            parsed_record = LogRecord(record)
            self.record = parsed_record
            self.is_error = False
            self.message = None
        except ParserError as e:
            self.record = None
            self.is_error = True
            self.message = str(e)


class LogfileProcessor:
    def __init__(self, notifiers, modules, log):

        self.log = log
        self.start = None
        self.end = None

        self.modules = {}
        for module in modules:
            obj = module(notifiers, log)
            self.modules[obj.identifier] = obj

    @staticmethod
    def logfile_reader(file_object):

        record = ''
        eof = False
        while not eof:
            line = file_object.readline()
            if line == '':
                data = record
                eof = True
                if data:
                    yield RecordResult(data)

            line = line.rstrip()
            if line and line[0] == '\x18':
                data = record
                record = line[1:]
                if data:
                    yield RecordResult(data)
            else:
                record += '{}\n'.format(line)

    def from_file(self, filename):
        with open(filename) as logfile:
            for result in self.logfile_reader(logfile):
                if result.is_error:
                    self.log.error('Error reading entry: {}'.format(result.message))
                else:
                    if (self.start is None or
                            result.record.timestamp < self.start):
                        self.start = result.record.timestamp

                    if (self.end is None or
                            result.record.timestamp > self.end):
                        self.end = result.record.timestamp

                    for module in list(self.modules.values()):
                        module.process_record(result.record)

    def log_stats(self):
        for module in list(self.modules.values()):
            self.log.info('Statistics for module {}'.format(module.description))
            module.log_statistics()
        self.log.info('Statistics ** Logfile wide **')

        if self.start:
            start_str = str(self.start)
        else:
            start_str = 'Undefined'

        if self.end:
            end_str = str(self.end)
        else:
            end_str = 'Undefined'

        self.log.info('Timestamp of first log entry: {}'.format(start_str))
        self.log.info('Timestamp of last log entry: {}'.format(end_str))
        if self.start and self.end:
            self.log.info('Log file Duration: {}'.format(self.end - self.start))

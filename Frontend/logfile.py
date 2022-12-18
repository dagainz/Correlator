import re
from datetime import datetime
from lib.util import ParserError

Priorities = {
    'perf': 7,
    'verbose': 6,
    'debug': 5,
    'info': 4,
    'notice': 3,
    'warning': 2,
    'error': 1
}
Default_priority = 1


class LogRecord:
    """Representation of a logfile record."""

    main_regex = r'(.{28}) (.+?) \[(.*?)\] (.*?) \[(.+?)\] (.+?): (.+)'

    def __init__(self, record, instance, hostname):
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
        severity = m.group(6).lower()
        self.priority = Priorities.get(severity, Default_priority)
        self.detail = m.group(7)
        self.instance = instance
        self.hostname = hostname
        # print("Severity: {}".format(self.severity))
        pass

    def __repr__(self):
        return "{} {} [{}] {} [{}] {}: {}".format(
            self.str_timestamp, self.who, self.request, self.prog,
            self.identifier, self.severity, self.detail)


class RecordResult:
    def __init__(self, record, instance, hostname):

        try:
            parsed_record = LogRecord(record, instance, hostname)
            self.record = parsed_record
            self.is_error = False
            self.message = None
        except ParserError as e:
            self.record = None
            self.is_error = True
            self.message = str(e)


class LogfileProcessor:
    def __init__(self, modules, log):

        self.log = log
        self.start = None
        self.end = None

        self.modules = modules

    @staticmethod
    def logfile_reader(file_object, instance, hostname):
        record = ''
        eof = False
        while not eof:
            line = file_object.readline()
            if line == '':
                data = record
                eof = True
                if data:
                    yield RecordResult(data, instance, hostname)

            line = line.rstrip()
            if line and line[0] == '\x18':
                data = record
                record = line[1:]
                if data:
                    yield RecordResult(data, instance, hostname)
            else:
                record += '{}\n'.format(line)

    def from_file(self, filename, instance, hostname):
        with open(filename) as logfile:
            for result in self.logfile_reader(logfile, instance, hostname):
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
            messages = module.statistics()
            for line in messages:
                self.log.info(line)
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

import re
from datetime import datetime
from mako.template import Template

from Correlator.event import (AuditEvent, EventProcessor)
from Correlator.util import (ParserError, Module, format_timestamp,
                             GlobalConfig)


class LogError(Exception):
    pass


class LogfileStatsEvent(AuditEvent):

    audit_id = 'system-stats'
    fields = ['start', 'end', 'duration']

    def __init__(self, data):
        super().__init__(self.audit_id, data)

        self.template_txt = Template(
            'Logfile processing session started at ${start} and ended at '
            '${end} for a total duration of ${duration}')


Priorities = {
    b'perf': 7,
    b'verbose': 6,
    b'debug': 5,
    b'info': 4,
    b'notice': 3,
    b'warning': 2,
    b'error': 1
}

Default_priority = 1


class LogRecord:

    main_regex = None

    def __init__(self, record):

        if self.main_regex is None:
            raise NotImplementedError

        m = re.match(self.main_regex, record)
        if not m:
            raise ParserError('Invalid logfile format')

        self.record = record
        self.match = m


class IDMLogRecord(LogRecord):
    """Representation of a logfile record."""

    main_regex = r'(.{28}) (.+?) \[(.*?)\] (.*?) \[(.+?)\] (.+?): (.+)'

    def __init__(self, record):

        super().__init__(record)

        m = self.match
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
        self.instance = GlobalConfig.get('idmsuite_instance')
        self.hostname = GlobalConfig.get('idmsuite_hosttname')

    def __repr__(self):
        return "{} {} [{}] {} [{}]: {}".format(
            self.str_timestamp, self.who, self.request, self.prog,
            self.identifier, self.detail)


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
    def __init__(self, log_record, modules: list[Module], log):

        self.log = log
        self.start = None
        self.end = None

        self.modules = modules
        self.log_record = log_record

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
            if line and line[0] == '\x18':
                data = record
                record = line[1:]
                if data:
                    yield RecordResult(data, self.log_record)
            else:
                record += '{}\n'.format(line)

    def from_file(self, filename):
        with open(filename) as logfile:
            for result in self.logfile_reader(logfile):
                if result.is_error:
                    self.log.error(
                        'Error reading entry: {}'.format(result.message))
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











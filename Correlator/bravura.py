import re
from datetime import datetime

from Correlator.syslog import SyslogRecord
from Correlator.logfile import LogRecord
from Correlator.util import GlobalConfig

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


class IDMLogRecord(LogRecord):
    """Log file record from Bravura Security Fabric."""

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
        return (f"{self.str_timestamp} {self.who} [{self.request}] {self.prog}"
                f" [{self.identifier}]: {self.detail}")


class IDMSyslogRecord(SyslogRecord):
    def __init__(self, record):
        super().__init__(record)

        # If superclass set the error, let it through
        if self.error:
            return

        self.who = ''
        self.request = ''

        if not self.proc_id:
            self.error = 'No proc-id in syslog record'
            return

        p = re.match(r'(.*)\((.+)\)', self.proc_id)
        if p:
            self.prog = p.group(1)
            self.identifier = p.group(2)
        else:
            self.prog = self.proc_id
            self.identifier = ''

        self.instance = self.appname


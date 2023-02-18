"""Support for Bravura Security Inc. Identity Management Software

To configure the logging service to forward log events that can be processed
by this system, an entry for this server needs to be defined in the 
SyslogCollectors section of the idmlogsvc.cfg file in the service subdirectory
of the Bravura Security Fabric instance:

"TCP=remote_server_name" "remote_server_port" = {

    # Syslog, not idmlog format
    LoggingAsSyslog = 1;

    # Include both Audit and Diagnostic messages.
    MessageType = Both;

    # CR
    EndOfLineStyle = 3;

    # Map all message levels to syslog severities.
    LoglevelToSeverity = {
              Critical = 2;   # only valid for audit messages.
              Error = 3;      # valid for both log and audit messages.
              Warning = 4;    # valid for both log and audit messages.
              Notice = 5;     # only valid for log messages.
              Info = 6;       # valid for both log and audit messages.
              Debug = 7;      # only valid for log messages.
              # ignore the Verbose level message
              Verbose = -1;   # only valid for log messages.
    };
};

"""

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

BRAVURA_SOFTWARE = (
    'Hitachi IDM Suite',
    'Bravura Security Fabric'
)


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


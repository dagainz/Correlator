import argparse
import logging
from datetime import datetime

from Correlator.event import (EventProcessor, LogbackListener, CSVListener)
from Correlator.logfile import (LogRecord, LogfileProcessor, Priorities,
                                Default_priority)

from Correlator.util import (Module, LogHelper, GlobalConfig)
from Correlator.Module.ucpath_queue import I280Queue


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
        return "{} {} [{}] {} [{}]: {}".format(
            self.str_timestamp, self.who, self.request, self.prog,
            self.identifier, self.detail)


def cli():

    log = logging.getLogger('logger')

    parser = argparse.ArgumentParser(
        'Bravura Security Fabric logfile processor')
    parser.add_argument(
        '--d', action='store_true', help='Show debugging messages"')
    parser.add_argument(
        '--csv', action='store_true',
        help='Write audit data for all modules to csv files')
    parser.add_argument('--logfile', help='Log file to parse', required=True)
    parser.add_argument('--instance', help='Instance name', required=True)
    parser.add_argument('--hostname', help='Host name', required=True)

    args = parser.parse_args()

    GlobalConfig.set('idmsuite_instance', args.instance)
    GlobalConfig.set('idmsuite_hostname', args.hostname)

    processor = EventProcessor(log)
    processor.register_listener(LogbackListener(log))
    if args.csv:
        processor.register_listener(CSVListener())

    # List of modules

    modules: list[Module] = [I280Queue(processor, log)]

    debug_level = logging.DEBUG if args.d else logging.INFO

    LogHelper.initialize_console_logging(log, debug_level)

    log.info('Starting')
    app = LogfileProcessor(IDMLogRecord, modules, log)
    app.from_file(args.logfile)
    app.log_stats(processor)


if __name__ == '__main__':
    cli()











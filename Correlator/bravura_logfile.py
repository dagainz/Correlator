import argparse
import logging

from Correlator.bravura import IDMLogRecord
from Correlator.event import (EventProcessor, LogbackListener, CSVListener)
from Correlator.logfile import LogfileProcessor
from Correlator.Module.ucpath_queue import I280Queue
from Correlator.util import (Module, setup_root_logger, GlobalConfig)


def cli():

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

    debug_level = logging.DEBUG if args.d else logging.INFO
    log = setup_root_logger(debug_level)

    GlobalConfig.set('idmsuite_instance', args.instance)
    GlobalConfig.set('idmsuite_hostname', args.hostname)

    # Setup event processing

    processor = EventProcessor()
    processor.register_listener(LogbackListener())
    if args.csv:
        processor.register_listener(CSVListener())

    # Build list of Correlator modules

    modules: list[Module] = [I280Queue(processor)]

    log.info('Starting')
    app = LogfileProcessor(IDMLogRecord, modules, log)
    app.from_file(args.logfile)
    app.log_stats(processor)


if __name__ == '__main__':
    cli()


import argparse
import logging
import os
import sys
from datetime import datetime

from Correlator.event import EventProcessor, LogbackListener
from Correlator.syslog import SyslogServer, SyslogStatsEvent
from Correlator.util import (LogHelper, capture_filename, format_timestamp)
from Correlator.Module.capture import CaptureOnly
from Correlator.Module.report import Report
from Correlator.Module.discovery import Discovery

log = logging.getLogger(__name__)


def cli():

    default_port = 514
    # default_bind_addr = '0.0.0.0'

    parser = argparse.ArgumentParser('Syslog ')
    parser.add_argument(
        '--d', help='Debug level', action='store_true'
    )
    parser.add_argument(
        '--port', help='TCP port to listen on', type=int, default=default_port
    )
    group = parser.add_mutually_exclusive_group()

    group.add_argument(
        '--write-file', metavar='filename', nargs='?', default='.',
        help='File to capture records and save to raw syslog capture file')

    group.add_argument(
        '--read-file', metavar='filename',
        help='raw syslog capture file to read and process')

    parser.add_argument(
        '--write-only', action='store_true',
        help='If writing to a capture file, do not process data.')

    parser.add_argument(
        '--report-only', action='store_true',
        help='Report on records processed. Do not take any action')

    cmd_args = parser.parse_args()

    # Hackery pokery to give a default value to write_file if not provided

    d = vars(cmd_args)

    if cmd_args.write_file is None:
        d['write_file'] = capture_filename()
    elif cmd_args.write_file == '.':
        d['write_file'] = None

    if cmd_args.write_only and not cmd_args.write_file:
        parser.error('--write-only requires --write-file')

    debug_level = logging.DEBUG if cmd_args.d else logging.INFO
    LogHelper.initialize_console_logging(log, debug_level)

    output_file = None

    if cmd_args.write_file:
        if os.path.exists(cmd_args.write_file):
            print("{} exists. Delete it first".format(cmd_args.write_file))
            sys.exit(0)
        else:
            log.info('Writing received syslog data to capture file {}'.format(
                cmd_args.write_file))
            output_file = open(cmd_args.write_file, 'wb')

    # Initialize event processor, and add event listeners

    processor = EventProcessor()
    processor.register_listener(LogbackListener())

    # Setup list of logic modules

    modules = []

    if cmd_args.write_only:
        modules.append(CaptureOnly(processor))
    else:
        if not cmd_args.report_only:
            # modules.append(I280Queue(processor, log))
            modules.append(Discovery(processor))
        else:
            modules.append(Report(processor))

    server = SyslogServer(modules, processor)

    if cmd_args.read_file:
        # Replay from capture file
        input_file = open(cmd_args.read_file, 'rb')
        log.info('Reading from capture file {} '.format(cmd_args.read_file))

        start = datetime.now()
        server.from_file(input_file)
        end = datetime.now()

        for module in modules:
            module.statistics()

        e = SyslogStatsEvent(
            {
                'start': format_timestamp(start),
                'end': format_timestamp(end),
                'duration': str(end - start)
            })
        e.system = 'syslog-server'
        processor.dispatch_event(e)
        return

    # Start network server

    start = datetime.now()
    log.info(
        'Server listening on port {}'.format(cmd_args.port))
    try:
        server.listen_single(port=cmd_args.port, output_file=output_file,
                             host='0.0.0.0')
    except KeyboardInterrupt:
        end = datetime.now()

        for module in modules:
            module.statistics()

        e = SyslogStatsEvent(
            {
                'start': format_timestamp(start),
                'end': format_timestamp(end),
                'duration': str(end - start)
            })
        e.system = 'syslog-server'
        processor.dispatch_event(e)
        log.info('Server shutting down')


if __name__ == '__main__':
    cli()

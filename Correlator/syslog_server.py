import argparse
import logging
import os
import sys
from datetime import datetime

from Correlator.event import EventProcessor, LogbackListener
from Correlator.syslog import SyslogServer, SyslogStatsEvent
from Correlator.util import (setup_root_logger, capture_filename,
                             format_timestamp)
from Correlator.Module.capture import CaptureOnly
from Correlator.Module.report import Report
from Correlator.Module.sshd import SSHD


def cli():

    default_port = 514
    default_bind_addr = '0.0.0.0'

    parser = argparse.ArgumentParser('Correlator Syslog CLI utility')

    parser.add_argument(
        '--d', help='Debug level', action='store_true'
    )
    parser.add_argument(
        '--port', help='TCP port to listen on', type=int, default=default_port
    )
    parser.add_argument(
        '--host', help='Address to listen on', type=str,
        default=default_bind_addr)

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

    # Give a default value to write_file if not provided

    d = vars(cmd_args)

    if cmd_args.write_file is None:
        d['write_file'] = capture_filename()
    elif cmd_args.write_file == '.':
        d['write_file'] = None

    if cmd_args.write_only and not cmd_args.write_file:
        parser.error('--write-only requires --write-file')

    debug_level = logging.DEBUG if cmd_args.d else logging.INFO
    setup_root_logger(debug_level)
    log = logging.getLogger(__name__)

    output_file = None

    if cmd_args.write_file:
        if os.path.exists(cmd_args.write_file):
            print(f'{cmd_args.write_file} exists. Delete it first')
            sys.exit(0)
        else:
            log.info(f'Writing received syslog data to capture file '
                     f'{cmd_args.write_file}')
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
            modules.append(SSHD(processor))
            # modules.append(I280Queue(processor, log))
            # modules.append(Discovery(processor))
            # todo: Fixme
            # modules.append(Report(processor))

        else:
            modules.append(Report(processor))

    server = SyslogServer(modules, processor)

    start = datetime.now()

    if cmd_args.read_file:
        # Replay from capture file
        log.info(f'Reading from capture file {cmd_args.read_file}')
        server.from_file(open(cmd_args.read_file, 'rb'))

    else:
        try:
            server.listen_single(port=cmd_args.port, output_file=output_file,
                                 host=cmd_args.host)
        except KeyboardInterrupt:
            pass

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


if __name__ == '__main__':
    cli()

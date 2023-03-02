""" Reference syslog server included with the Correlator library

- Reads from the network or capture file, optionally writing records received
  over the network to a capture file.
- Use or test modules included with this library.


"""
import argparse
import logging
import os
import sys
from datetime import datetime

from Correlator.event import EventProcessor, LogbackListener
from Correlator.Module.report import Report
from Correlator.Module.sshd import SSHD
from Correlator.syslog import SyslogServer, SyslogStatsEvent
from Correlator.util import (
    setup_root_logger, capture_filename, format_timestamp)


def cli():

    default_port = 514
    default_bind_addr = '0.0.0.0'

    parser = argparse.ArgumentParser(
        'Correlator Syslog CLI utility',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)

    parser.add_argument(
        '--d',
        help='Debug level', action='store_true'
    )
    parser.add_argument(
        '--port',
        help='TCP port to listen on', type=int, default=default_port
    )
    parser.add_argument(
        '--host',
        help='Address to listen on', type=str, default=default_bind_addr)

    group = parser.add_mutually_exclusive_group()

    group.add_argument(
        '--write-file',
        metavar='filename', nargs='?', default='.',
        help='File to capture records and save to raw syslog capture file')

    group.add_argument(
        '--read-file',
        metavar='filename', help='raw syslog capture file to read and process')

    parser.add_argument(
        '--sshd',
        action='store_true', help='Activate ssh login module')

    cmd_args = parser.parse_args()

    # Give a default value to write_file if not provided

    d = vars(cmd_args)

    if cmd_args.write_file is None:
        d['write_file'] = capture_filename()
    elif cmd_args.write_file == '.':
        d['write_file'] = None

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

    # Add all modules specified on the command line

    if cmd_args.sshd:
        modules.append(SSHD(processor))

    # If any weren't added,add the Report module

    if not modules:
        modules.append(Report(processor))

    server = SyslogServer(modules, processor)

    start = datetime.now()

    if cmd_args.read_file:
        # Replay from capture file
        log.info(f'Reading from capture file {cmd_args.read_file}')
        server.from_file(open(cmd_args.read_file, 'rb'))

    else:
        stop = False
        while not stop:
            try:
                server.listen_single(
                    port=cmd_args.port,
                    output_file=output_file,
                    host=cmd_args.host)
            except KeyboardInterrupt:
                log.info('Shutting down')
                stop = True

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

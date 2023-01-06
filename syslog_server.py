#!python3

import argparse
import logging
import os
import sys
import socketserver
from datetime import datetime

from Frontend.syslog import SyslogHandler
from Notify.notify import Notifiers, LogbackNotify
from Module.ucpath_queue import I280Queue
from Module.capture import CaptureOnly
from Module.report import Report
from lib.util import LogHelper, build_modules, capture_filename

log = logging.getLogger('logger')

default_port = 514
default_bind_addr = '0.0.0.0'

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

listening = True
tcpServer = None
single_thread = True

input_file = None
output_file = None

if cmd_args.write_file:
    if os.path.exists(cmd_args.write_file):
        print("{} exists. Delete it first".format(cmd_args.write_file))
        sys.exit(0)
    else:
        log.info('Writing received syslog data to capture file {}'.format(
            cmd_args.write_file))
        output_file = open(cmd_args.write_file, 'wb')


module_notifiers = Notifiers()
if cmd_args.write_only:
    module_notifiers.add_notifier(LogbackNotify(log, 'MODULE'))
    modules = build_modules([CaptureOnly], module_notifiers, log)
else:
    module_notifiers.add_notifier(LogbackNotify(log, 'MODULE'))
    if not cmd_args.report_only:
        modules = build_modules(
            [I280Queue],
            module_notifiers,
            log)
    else:
        modules = build_modules(
            [Report],
            module_notifiers,
            log)

system_notifiers = Notifiers()
system_notifiers.add_notifier(LogbackNotify(log, 'SYSTEM'))

props = {
    'output_file': output_file,
    'modules': modules,
    'module_notifiers': module_notifiers,
    'log': log
}

# Create a new class based on the metaclass, with these properties
# possibly overridden.
#

CustomSyslogHandler = type(
    'CustomSyslogHandler', (SyslogHandler,), props)

if cmd_args.read_file:
    # Replay from capture file
    input_file = open(cmd_args.read_file, 'rb')
    log.info('Reading from capture file {} '.format(cmd_args.read_file))
    CustomSyslogHandler(input_file)
    sys.exit(0)

if single_thread:
    # Create the server, binding to interface and port

    with socketserver.TCPServer(
            (default_bind_addr, cmd_args.port), CustomSyslogHandler) as server:
        # Activate the server and run until Ctrl-C
        try:
            start = datetime.now()
            log.info(
                'Server listening on port {}'.format(cmd_args.port))
            server.serve_forever()
        except KeyboardInterrupt:

            end = datetime.now()

            for module in list(modules.values()):
                log.info(
                    'Statistics for module {}'.format(module.description))
                messages = module.statistics()
                for line in messages:
                    log.info(line)

            log.info('Statistics ** Server session wide **')
            log.info(
                'Server session started: {}'.format(str(start)))
            log.info(
                'Server session ended: {}'.format(str(end)))
            log.info(
                'Server session duration: {}'.format(str(end-start)))
else:
    ValueError('No multi thread at this time')

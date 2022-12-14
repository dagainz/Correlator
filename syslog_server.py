#!python3

import argparse
import logging
import os
import sys
import socketserver
from datetime import datetime

from Frontend.syslog import SyslogHandler
from Notify.notify import Notifiers, ConsoleNotify, LogbackNotify
from Module.ucpath_queue import I280Queue
from Module.capture import CaptureOnly
from lib.util import LogHelper, build_modules

log = logging.getLogger('logger')


syslog_host = '0.0.0.0'

parser = argparse.ArgumentParser('Syslog ')
parser.add_argument(
    '--d', help='Debug level', action='store_true'
)
parser.add_argument(
    '--port', help='TCP port to listen on', type=int, default=514
)
group = parser.add_mutually_exclusive_group()

group.add_argument(
    '--write-to-file', metavar='filename',
    help='File to capture records and save to raw syslog capture file')

group.add_argument(
    '--read-from-file', metavar='filename',
    help='raw syslog capture file to read and process')

parser.add_argument(
    '--write-only', action='store_true',
    help='If writing to a capture file, do not process data.')


cmd_args = parser.parse_args()
if cmd_args.write_only and not cmd_args.write_to_file:
    parser.error('--write-only requires --write-to-file')

debug_level = logging.DEBUG if cmd_args.d else logging.INFO
LogHelper.initialize_console_logging(log, debug_level)

listening = True
tcpServer = None
single_thread = True

input_file = None
output_file = None

if cmd_args.write_to_file:
    if os.path.exists(cmd_args.write_to_file):
        print("{} exists. Delete it first".format(cmd_args.write_to_file))
        sys.exit(0)
    else:
        log.info('Writing received syslog data to capture file {}'.format(
            cmd_args.write_to_file))
        output_file = open(cmd_args.write_to_file, 'wb')


notifiers = Notifiers()
if cmd_args.write_only:
    notifiers.add_notifier(LogbackNotify(log))
    modules = build_modules([CaptureOnly], notifiers, log)
else:
    notifiers.add_notifier(LogbackNotify(LogbackNotify(log)))

    modules = build_modules(
        [I280Queue],
        notifiers,
        log)


props = {
    'output_file': output_file,
    'modules': modules,
    'notifiers': notifiers,
    'log': log
}

# Create a new class based on the metaclass, with these properties
# possibly overridden.
#

CustomSyslogHandler = type(
    'CustomSyslogHandler', (SyslogHandler,), props)

if cmd_args.read_from_file:
    # Replay from capture file
    input_file = open(cmd_args.read_from_file, 'rb')
    log.info('Reading from capture file {} '.format(cmd_args.read_from_file))
    CustomSyslogHandler(input_file)
    sys.exit(0)

if single_thread:
    # Create the server, binding to interface and port

    with socketserver.TCPServer(
            (syslog_host, cmd_args.port), CustomSyslogHandler) as server:
        # Activate the server and run until Ctrl-C
        try:
            start = datetime.now()
            log.info(
                'Server listening on port {}'.format(cmd_args.port))
            server.serve_forever()
        except KeyboardInterrupt:

            end = datetime.now()

            for module in list(modules.values()):
                notifiers.send_info(
                    'Statistics for module {}'.format(module.description))
                module.log_statistics()

            log.info('Statistics ** Server session wide **')
            log.info(
                'Server session started: {}'.format(str(start)))
            log.info(
                'Server session ended: {}'.format(str(end)))
            log.info(
                'Server session duration: {}'.format(str(end-start)))
else:
    ValueError('No multi thread at this time')

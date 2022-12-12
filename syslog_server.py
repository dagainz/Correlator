#!python3

import argparse
import logging
import os
import sys
import socketserver

from Frontend.syslog import SyslogHandler
from Notify.notify import Notifiers, ConsoleNotify, CSVNotify
from Module.ucpath_queue import I280Queue
from lib.util import LogHelper, build_modules

log = logging.getLogger('logger')


syslog_host = '0.0.0.0'
syslog_tcp_port = 514

parser = argparse.ArgumentParser('Syslog ')
group = parser.add_mutually_exclusive_group()
parser.add_argument(
    '--d', help='Debug level', action='store_true'
)

group.add_argument(
    '--save-records',
    help='File to save syslog records to (implies single thread)')
group.add_argument(
    '--read-records',
    help='File to read and process saved syslog records')

cmd_args = parser.parse_args()
debug_level = logging.DEBUG if cmd_args.d else logging.INFO
LogHelper.initialize_console_logging(log, debug_level)

# Set up the notifier chain
notifiers = Notifiers()
# Add the basic console notifier
notifiers.add_notifier(ConsoleNotify())

# List of modules

modules = build_modules(
    [I280Queue],
    notifiers,
    log)

# logging.basicConfig(level=logging.INFO, format='%(message)s', datefmt='', filename=LOG_FILE, filemode='a')

listening = True
tcpServer = None
single_thread = True

# log = None
# modules = None
input_file = None
output_file = None
# notifiers = notifiers

if cmd_args.read_records:
    # Replay from capture file
    input_file = open(cmd_args.read_records, 'rb')
    log.info('Reading from capture file {} '.format(cmd_args.read_records))
    SyslogHandler(input_file)
    sys.exit(0)
elif cmd_args.save_records:
    if os.path.exists(cmd_args.save_records):
        print("{} exists. Delete it first".format(cmd_args.save_records))
        sys.exit(0)
    else:
        log.info('Writing received syslog data to capture file {}'.format(
            cmd_args.save_records))
        output_file = open(cmd_args.save_records, 'wb')


props = {
    'output_file': output_file,
    'modules': modules,
    'notifiers': notifiers,
    'log': log
}

# Create a new class based on the meta class, with these properties
# possibly overridden.
#
CustomSyslogHandler = type (
    'CustomSyslogHandler', (SyslogHandler,), props)


if single_thread:
    # Create the server, binding to interface and port
    with socketserver.TCPServer(
            (syslog_host, syslog_tcp_port), CustomSyslogHandler) as server:
        # Activate the server and run until Ctrl-C
        server.serve_forever()
else:
    ValueError('No multi thread at this time')

#!python3

import argparse
import logging
import os
import socketserver
import sys
from datetime import datetime
from mako.template import Template

from common.event import EventProcessor, LogbackListener, AuditEvent
from common.syslog import SyslogHandler
from common.util import LogHelper, capture_filename, Module, format_timestamp
from Module.capture import CaptureOnly
from Module.report import Report
from Module.ucpath_queue import I280Queue


class StatsEvent(AuditEvent):

    audit_id = 'system-stats'
    fields = ['start', 'end', 'duration']

    def __init__(self, data):
        super().__init__(self.audit_id, data)

        self.template_txt = Template(
            'Severs session started at ${start} and ended at ${end} for a '
            'total duration of ${duration}')


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

# Initialize event processor, and add event listeners

processor = EventProcessor(log)
processor.register_listener(LogbackListener(log))

# Setup list of logic modules

modules: list[Module] = []

if cmd_args.write_only:
    modules.append(CaptureOnly(processor, log))
else:
    if not cmd_args.report_only:
        modules.append(I280Queue(processor, log))
    else:
        modules.append(Report(processor, log))

props = {
    'output_file': output_file,
    'modules': modules,
    'processor': processor,
    'log': log
}

# Create a new class based on the metaclass, with these properties
# possibly overridden.

CustomSyslogHandler = type(
    'CustomSyslogHandler', (SyslogHandler,), props)

if cmd_args.read_file:
    # Replay from capture file
    input_file = open(cmd_args.read_file, 'rb')
    log.info('Reading from capture file {} '.format(cmd_args.read_file))

    start = datetime.now()
    CustomSyslogHandler(input_file)
    end = datetime.now()

    for module in modules:
        module.statistics()

    e = StatsEvent(
        {
            'start': format_timestamp(start),
            'end': format_timestamp(end),
            'duration': str(end - start)
        })
    e.system = 'syslog-server'
    processor.dispatch_event(e)
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

            for module in modules:
                module.statistics()

            e = StatsEvent(
                {
                    'start': format_timestamp(start),
                    'end': format_timestamp(end),
                    'duration': str(end-start)
                })
            e.system = 'syslog-server'
            processor.dispatch_event(e)
else:
    ValueError('No multi thread at this time')

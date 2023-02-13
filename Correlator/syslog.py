import argparse
import iso8601
import logging
import os
import re
import socketserver
import sys
from typing import List, Union
from datetime import datetime
from mako.template import Template
from io import BufferedReader

from Correlator.event import (EventProcessor, LogbackListener, AuditEvent,
                              ErrorEvent)
# from Correlator.syslog import SyslogHandler
from Correlator.util import (LogHelper, capture_filename, Module,
                             format_timestamp, ParserError)
from Correlator.Module.capture import CaptureOnly
from Correlator.Module.report import Report
from Correlator.Module.discovery import Discovery


output_file = None
input_file = None


class SyslogStatsEvent(AuditEvent):

    audit_id = 'system-stats'
    fields = ['start', 'end', 'duration']

    def __init__(self, data):
        super().__init__(self.audit_id, data)

        self.template_txt = Template(
            'Sever session started at ${start} and ended at ${end} for a '
            'total duration of ${duration}')


class SyslogRecord:

    main_regex = (
            r'<(?P<priority>\d+?)>(?P<version>\d) (?P<timestamp_str>.+?) '
            r'(?P<hostname>.+?) (?P<appname>.+?) (?P<procid>.+?) (?P<msgid>.+?)'
            r' (?P<rest>.+)')

    def __init__(self, record):

        self.original_record = record
        self.record_length = len(record)
        self.error = None

        pos = record.find(b'\xef\xbb\xbf')

        if pos:
            decoded_record = (
                    record[0:pos].decode('utf-8')
                    + record[pos + 3:].decode('utf-8'))
        else:
            decoded_record = record.decode('utf-8')

        self.m = re.match(self.main_regex, decoded_record)

        if not self.m:
            self.error = "1st stage parse failure"
            return

        self.timestamp_str = self.m.group('timestamp_str')
        try:
            self.timestamp = iso8601.parse_date(self.timestamp_str)
        except iso8601.ParseError:
            self.error = 'Cannot parse timestamp'
            return

        self.priority = self.m.group('priority')
        self.hostname = self.m.group('hostname')
        self.appname = self.m.group('appname')
        self.procid = self.m.group('procid')
        self.msgid = self.m.group('msgid')

        try:
            self.detail, self.structured_data = self._parse_sdata(
                self.m.group('rest'))
        except ParserError as e:
            self.error = 'Cannot parse structured data: {}'.format(e)
            return

    @staticmethod
    def _parse_sdata(dataline):

        has_structured_data = False
        element_id = None
        state = 1
        parsed_struc = {}

        def add_param(eid, param_key, param_value):
            if element_id not in parsed_struc:
                parsed_struc[eid] = {}

            parsed_struc[eid][param_key] = param_value

        while True:
            if not dataline:
                raise ParserError('Ran out of content')
            if state == 1:

                if not has_structured_data and dataline[0:2] == '- ':
                    return dataline[2:], {}

                m = re.match(r'\[(\w+) (.*)', dataline)
                if not m:
                    if not has_structured_data:
                        raise ParserError(
                            'SD-DATA {} parse failed '.format(dataline))
                    else:
                        return dataline.lstrip(), parsed_struc
                element_id = m.group(1)
                dataline = m.group(2)
                state = 2
                continue
            elif state == 2:
                m = re.match(r'\](.*)', dataline)
                if m:
                    dataline = m.group(1)
                    state = 1
                    continue
                m = re.match(r'(.+?)="*([^"]+)"\s*(.*)', dataline)
                if m:
                    add_param(element_id, m.group(1), m.group(2))
                    has_structured_data = True
                    dataline = m.group(3)
                    continue
                else:
                    raise ParserError(
                        'SD-DATA Key/Value {} parse failed'.format(
                            dataline))

    def __repr__(self):
        return '{} ({})'.format(self.m.groupdict(), self.structured_data)

    def __len__(self):
        return self.record_length


class IDMSyslogRecord(SyslogRecord):
    def __init__(self, record):
        super().__init__(record)

        # If superclass set the error, let it through
        if self.error:
            return

        self.who = ''
        self.request = ''

        if not self.procid:
            self.error = 'No proc-id in syslog record'
            return

        p = re.match(r'(.*)\((.+)\)', self.procid)
        if p:
            self.prog = p.group(1)
            self.identifier = p.group(2)
        else:
            self.prog = self.procid
            self.identifier = ''

        self.instance = self.appname


class SyslogHandler(socketserver.BaseRequestHandler):

    # This is a template class, meant to be dynamically generated via type,
    # because instantiation and initialization happens somewhere in
    # socketserver, and I can't think of an elegant way to have these
    # variables be available to the handler.

    # These properties can be set via this method

    output_file: Union[None, BufferedReader] = None
    modules: List[Module] = []
    log = None
    processor: Union[None, EventProcessor] = None

    # Start of handler

    BUFFER_SIZE = 1024

    def __init__(self, *args):
        if len(args) == 1:      # from-file context
            # In this case, we don't want to call the superclass constructor,
            # We'll just handle it our self.
            self.input_file = args[0]
            self.handle()
        else:
            self.input_file = None
            super().__init__(*args)

    def process_record(self, data):
        record = IDMSyslogRecord(data)
        if not record.error:
            for module in self.modules:
                module.process_record(record)
        else:
            self.processor.dispatch_event(
                ErrorEvent(
                    'Error processing record',
                    data=data))

    def handle(self):
        last = b''
        while True:
            if self.input_file:
                block = self.input_file.read(self.BUFFER_SIZE)
            else:
                block = self.request.recv(self.BUFFER_SIZE)
            if block:
                if self.output_file:
                    self.output_file.write(block)
            data = last + block
            if not data:
                break
            last = self._handle_records(data)

    def _handle_records(self, data):

        while True:
            pos = data.find(b'\r')
            if pos == -1:
                return data
            self.process_record(data[0:pos])
            data = data[pos + 1:]


def CLI():
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
            # modules.append(I280Queue(processor, log))
            modules.append(Discovery(processor, log))
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

        e = SyslogStatsEvent(
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
                (default_bind_addr, cmd_args.port),
                CustomSyslogHandler) as server:
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

                e = SyslogStatsEvent(
                    {
                        'start': format_timestamp(start),
                        'end': format_timestamp(end),
                        'duration': str(end - start)
                    })
                e.system = 'syslog-server'
                processor.dispatch_event(e)
    else:
        ValueError('No multi thread at this time')

if __name__ == '__main__':
    CLI()

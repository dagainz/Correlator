#!/usr/bin/env python

from datetime import datetime
import iso8601
import re
import socketserver

from util import ParserError

output_file = None
input_file = None


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

    output_file = None
    modules = None
    log = None

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
            for module in list(self.modules.values()):
                module.process_record(record)
        else:
            self.log.error('{}\nRecord: {}'.format(
                record.error, record.original_record))
                # print('Process record: {}'.format(record))

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




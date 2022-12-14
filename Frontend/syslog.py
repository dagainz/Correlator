#!/usr/bin/env python

from datetime import datetime
import iso8601
import re
import socketserver

from lib.util import ParserError

output_file = None
input_file = None


class SyslogRecord:

    main_regex = (
            r'<(?P<priority>\d+?)>(?P<version>\d) (?P<timestamp_str>.+?) '
            r'(?P<hostname>.+?) (?P<appname>.+?) (?P<procid>.+?) (?P<msgid>.+?)'
            r' (?P<structure>\[.+\]|-) (?P<detail>.+)')
    sd_element_regex = r'\[(\w+) ([^\]]+?)\](.*)'
    sd_param_regex = r'(.+?)="(.*?)"\s?(.*)'

    def __init__(self, record):

        self.record_length = len(record)
        pos = record.find(b'\xef\xbb\xbf')
        if pos:
            decoded_record = (
                    record[0:pos].decode('utf-8')
                    + record[pos + 3:].decode('utf-8'))
        else:
            decoded_record = record.decode('utf-8')

        # print("DEBUG: Matching {}".format(decoded_record))
        # print("DEBUG: against {}".format(self.main_regex))

        self.m = re.match(self.main_regex, decoded_record)

        if not self.m:
            raise ValueError('Invalid syslog record')

        self.sd_data = {}

        # Decode RFC 5424 STRUCTURED-DATA
        structure = self.m.group('structure')
        while True:
            # Read an SD-ELEMENT
            sd_elem = re.match(self.sd_element_regex, structure)
            if sd_elem:
                sd_elem_id = sd_elem.group(1)
                sd_elem_data = sd_elem.group(2)
                sd_elem_remaining = sd_elem.group(3)
                while True:
                    # Read an SD-PARAM
                    sd_param = re.match(self.sd_param_regex, sd_elem_data)
                    if sd_param:
                        sd_param_key = sd_param.group(1)
                        sd_param_value = sd_param.group(2)
                        sd_param_remaining = sd_param.group(3)

                        # Add k/v

                        if sd_elem_id not in self.sd_data:
                            self.sd_data[sd_elem_id] = {}

                        # Add key/value pair
                        self.sd_data[sd_elem_id][sd_param_key] = sd_param_value

                        # Keep parsing SD-PARAM's if there are any
                        if sd_param_remaining:
                            sd_elem_data = sd_param_remaining
                        else:
                            # Last (or only) SD-PARAM
                            break
                    else:
                        raise ParserError(
                            'SD-PARAM regex did not match ({})'.format(
                                sd_elem_data
                            ))
                if sd_elem_remaining:
                    # Keep parsing SD-ELEMENT'S if there are any
                    structure = sd_elem_remaining
                else:
                    break

        self.timestamp_str = self.m.group('timestamp_str')
        try:
            self.timestamp = iso8601.parse_date(self.timestamp_str)
        except iso8601.ParseError:
            self.timestamp = None

        self.priority = self.m.group('priority')
        self.hostname = self.m.group('hostname')
        self.appname = self.m.group('appname')
        self.procid = self.m.group('procid')
        self.msgid = self.m.group('msgid')
        self.detail = self.m.group('detail')

        # Properties

    def __repr__(self):
        return '{} ({})'.format(self.m.groupdict(), self.sd_data)

    def __len__(self):
        return self.record_length


class IDMSyslogRecord(SyslogRecord):
    def __init__(self, record):
        super().__init__(record)

        self.who = ''
        self.request = ''

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
        for module in list(self.modules.values()):
            module.process_record(record)
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
            pos = data.find(b'\n')
            if pos == -1:
                return data
            self.process_record(data[0:pos])
            data = data[pos + 1:]




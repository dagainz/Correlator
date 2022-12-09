#!/usr/bin/env python

import re
import socketserver

from lib.util import ParserError

output_file = None
input_file = None


class SyslogRecord:

    main_regex = (
            r'<(?P<priority>\d+?)>(?P<version>\d) (?P<timestamp_str>.+?) '
            r'(?P<hostname>.+?) (?P<appname>.+?) (?P<procid>.+?) (?P<msgid>.+?)'
            r' (?P<structure>\[.+\]|-) (?P<message>.+)')
    sd_element_regex = r'\[(\w+) ([^\]]+?)\](.*)'
    sd_param_regex = r'(.+?)="(.*?)"\s?(.*)'

    def __init__(self, record):

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

        self.structured_data = {}

        # Decode RFC 5424 STRUCTURED-DATA
        structure = self.m.group('structure')
        while True:
            # Read an SD-ELEMENT
            sd_element = re.match(self.sd_element_regex, structure)
            if sd_element:
                sd_element_id = sd_element.group(1)
                sd_element_data = sd_element.group(2)
                sd_element_remaining = sd_element.group(3)
                while True:
                    # Read an SD-PARAM
                    sd_param = re.match(self.sd_param_regex, sd_element_data)
                    if sd_param:
                        sd_param_key = sd_param.group(1)
                        sd_param_value = sd_param.group(2)
                        sd_param_remaining = sd_param.group(3)

                        # Add k/v

                        if sd_element_id not in self.structured_data:
                            self.structured_data[sd_element_id] = {}

                        # Add key/value pair
                        self.structured_data[sd_element_id][sd_param_key] = sd_param_value

                        # Keep parsing SD-PARAM's if there are any
                        if sd_param_remaining:
                            sd_element_data = sd_param_remaining
                        else:
                            # Last (or only) SD-PARAM
                            break
                    else:
                        raise ParserError('SD-PARAM regex did not match')
                if sd_element_remaining:
                    # Keep parsing SD-ELEMENT'S if there are any
                    structure = sd_element_remaining
                else:
                    break

        self.timestamp_str = self.m.group('timestamp_str')
        self.priority = self.m.group('priority')
        self.hostname = self.m.group('hostname')
        self.appname = self.m.group('appname')
        self.procid = self.m.group('procid')
        self.msgid = self.m.group('msgid')
        self.message = self.m.group('message')

    def __repr__(self):
        return '{} ({})'.format(self.m.groupdict(), self.structured_data)


class SyslogTCPHandler(socketserver.BaseRequestHandler):

    output_file = None
    BUFFER_SIZE = 24

    @staticmethod
    def handle_record(data):
        record = SyslogRecord(data)
        print('Process record: {}'.format(record))

    def handle_records(self, data):

        while True:
            pos = data.find(b'\n')
            if pos == -1:
                return data
            self.handle_record(data[0:pos])
            data = data[pos + 1:]

    def handle(self):
        last = b''
        while True:
            block = self.request.recv(24)
            if self.output_file:
                self.output_file.write(block)
            data = last + block
            if not data:
                break
            last = self.handle_records(data)


class SyslogFromFile:
    def __init__(self, file_object):
        self.input_file = file_object

    @staticmethod
    def handle_record(data):
        record = SyslogRecord(data)
        print('Process record: {}'.format(record))

    def handle_records(self, data):

        while True:
            pos = data.find(b'\n')
            if pos == -1:
                return data
            self.handle_record(data[0:pos])
            data = data[pos + 1:]

    def handle(self):
        last = b''
        while True:
            data = last + self.input_file.read(24)
            if not data:
                break
            last = self.handle_records(data)




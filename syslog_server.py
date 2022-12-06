#!/usr/bin/env python

import argparse
import logging
import os
import time
import threading
import re
import socketserver

output_file = None
input_file = None

class SyslogRecord:

    main_regex = (
            r'<(?P<priority>\d+?)>(?P<version>\d) (?P<timestamp_str>.+?) (?P<hostname>.+?) (?P<appname>.+?) ' +
            r'(?P<procid>.+?) (?P<msgid>.+?) (?P<structure>\[.+\]|-) (?P<message>.+)')
    struc_regex = r'\[(\w+) ([^\]]+?)\](.*)'
    struc_data_regex = r'(.+?)="(.*?)"\s?(.*)'

    def __init__(self, record):

        pos = record.find(b'\xef\xbb\xbf')
        if pos:
            decoded_record = record[0:pos].decode('utf-8') + record[pos + 3:].decode('utf-8')
        else:
            decoded_record = record.decode('utf-8')

        # print("DEBUG: Matching {}".format(decoded_record))
        # print("DEBUG: against {}".format(self.main_regex))

        self.m = re.match(self.main_regex, decoded_record)
        if self.m:
            self.structured_data = {}
            print('Data: {}'.format(self.__repr__()))
            structure = self.m.group('structure')
            while True:
                # print("Matching {} against {}".format(structure, self.struc_regex))
                s = re.match(self.struc_regex, structure)
                if s:
                    sd_id = s.group(1)
                    sd_data = s.group(2)
                    sd_next = s.group(3)
                    while True:
                        # print("Matching{} against {}".format(sd_data, self.struc_data_regex))
                        i = re.match(self.struc_data_regex, sd_data)
                        if i:
                            sd_key = i.group(1)
                            sd_value = i.group(2)
                            kv_next  = i.group(3)
                            if sd_id not in self.structured_data:
                                self.structured_data[sd_id] = {}

                            self.structured_data[sd_id][sd_key] = sd_value
                            if kv_next:
                                sd_data = kv_next
                            else:
                                break
                        else:
                            break
                    if sd_next:
                        structure = sd_next
                    else:
                        break

            print('Data: {}'.format(self.__repr__()))

        else:
            raise ValueError('Invalid syslog record')

    def __repr__(self):
        return '{} ({})'.format(self.m.groupdict(), self.structured_data)


class SyslogFileHandler:

    def __init__(self, file_handle):
        self.file_handle = file_handle

    @staticmethod
    def handle_record(data):
        record = SyslogRecord(data)

    def handle_records(self, data):
        if output_file:
            output_file.write(data)

        while True:
            pos = data.find(b'\n')
            if pos == -1:
                return data
            self.handle_record(data[0:pos])
            data = data[pos + 1:]

    def handle(self):
        last = b''
        while True:
            data = last + input_file.read(24)
            if not data:
                break
            last = self.handle_records(data)


class SyslogTCPHandler(socketserver.BaseRequestHandler):

    @staticmethod
    def handle_record(data):
        record = SyslogRecord(data)

    def handle_records(self, data):

        while True:
            pos = data.find(b'\n')
            if pos == -1:
                return data
            self.handle_record(data[0:pos])
            data = data[pos + 1:]

    def handle(self):
        last = b''
        while listening:
            block = self.request.recv(24)
            if output_file:
                output_file.write(block)
            data = last + block
            if not data:
                break
            last = self.handle_records(data)


syslog_host = '0.0.0.0'
syslog_tcp_port = 514

parser = argparse.ArgumentParser('Log tool CLI')
group = parser.add_mutually_exclusive_group()

group.add_argument('--save-records', help='File to save syslog records to (implies single thread)')
group.add_argument('--read-records', help='File to read and process saved syslog records')

cmd_args = parser.parse_args()

# logging.basicConfig(level=logging.INFO, format='%(message)s', datefmt='', filename=LOG_FILE, filemode='a')

listening = True
tcpServer = None
single_thread = True

if cmd_args.save_records:
    if os.path.exists(cmd_args.save_records):
        print ("Will not overwrite {}. Remove it first.".format(cmd_args.save_records))
    else:
        output_file = open(cmd_args.save_records, 'wb')
if cmd_args.read_records:
    input_file = open(cmd_args.read_records, 'rb')
    SyslogFileHandler(input_file).handle()
else :
    if single_thread:
        # Create the server, binding to interface and port
        with socketserver.TCPServer((syslog_host, syslog_tcp_port), SyslogTCPHandler) as server:
            # Activate the server and run until Ctrl-C
            server.serve_forever()
    else:
        ValueError('No multi thread at this time')

# listening = True
# tcpServer = None
#
# try:
#
#     # TCP server
#     tcpServer = socketserver.TCPServer((HOST, TCP_PORT), SyslogTCPHandler)
#     tcpThread = threading.Thread(target=tcpServer.serve_forever)
#     tcpThread.daemon = True
#     tcpThread.start()
#
#     while True:
#         time.sleep(1)
# # tcpServer.serve_forever(poll_interval=0.5)
# except (IOError, SystemExit):
#     raise
# except KeyboardInterrupt:
#     listening = False
#     if tcpServer:
#         tcpServer.shutdown()
#         tcpServer.server_close()
#     print("Crtl+C Pressed. Shutting down.")

#!python3

import argparse
import os
import sys
import socketserver

from Frontend.syslog import SyslogFromFile, SyslogTCPHandler

output_file = None

syslog_host = '0.0.0.0'
syslog_tcp_port = 514

parser = argparse.ArgumentParser('Syslog ')
group = parser.add_mutually_exclusive_group()

group.add_argument(
    '--save-records',
    help='File to save syslog records to (implies single thread)')
group.add_argument(
    '--read-records',
    help='File to read and process saved syslog records')

cmd_args = parser.parse_args()

# logging.basicConfig(level=logging.INFO, format='%(message)s', datefmt='', filename=LOG_FILE, filemode='a')

listening = True
tcpServer = None
single_thread = True

if cmd_args.read_records:
    # Replay from capture file
    SyslogFromFile(open(cmd_args.read_records, 'rb')).handle()
    sys.exit(0)

if cmd_args.save_records:
    if os.path.exists(cmd_args.save_records):
        print("Will not overwrite {}. Remove it first.".format(cmd_args.save_records))
        sys.exit(0)
    else:
        output_file = open(cmd_args.save_records, 'wb')
        handler_object = type('SyslogTCPWriterHandler', (SyslogTCPHandler, ), {'output_file': output_file})
else:
    handler_object = SyslogTCPHandler

if single_thread:
    # Create the server, binding to interface and port
    with socketserver.TCPServer((syslog_host, syslog_tcp_port), handler_object) as server:
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

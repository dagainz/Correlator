import iso8601
import logging
import re
import socket
from mako.template import Template
from typing import List, BinaryIO, Callable

from Correlator.event import EventProcessor, ErrorEvent, AuditEvent
from Correlator.util import ParserError, Module

DEFAULT_SYSLOG_TRAILER = b'\n'

# This must be big enough to hold enough of a syslog record to guarantee that
# it contains the entire structured data for trailer discovery.

DEFAULT_BUFFER_SIZE = 4096

log = logging.getLogger(__name__)


class SyslogServer:
    """ Handles listening for and processing Syslog data from the network.

    :param modules: A list of Correlator Modules
    :type modules: List[Module]
    :param processor: The event processor object
    :type processor: EventProcessor

    """
    def __init__(self, modules: List[Module], processor: EventProcessor,
                 trailer_discovery_method: Callable[[dict], bytes] = None):

        self.modules = modules
        self.processor = processor
        self.buffer_size: int = DEFAULT_BUFFER_SIZE
        self.syslog_trailer = None
        self.trailer_discovery_method = trailer_discovery_method

    def from_file(self, file_obj: BinaryIO):
        """ Processes saved syslog data from a file

        :param file_obj: File object of a readable binary file
        :type file_obj: typing.BinaryIO

        """

        last = b''
        while True:
            block = file_obj.read(self.buffer_size)

            # Find our trailer (syslog record seperator) if
            # We haven't already.

            if self.syslog_trailer is None:
                self.syslog_trailer = self.discover_trailer(block)
                if self.syslog_trailer is None:
                    self.processor.dispatch_event(
                        ErrorEvent(
                            'Problem running trailer discovery'))
                    return

            data = last + block
            if not data:
                return
            last = self._handle_records(data)

    def listen_single(self, host: str = None,
                      port: int = 514,
                      output_file: BinaryIO = None):

        """ Single threaded network listener.

         Will write captured network data to the opened for writing binary
         file output_file if provided.

         :param host: hostname or interface to listen on
         :type host: str
         :param port: Port number to listen on (default 514)
         :type port: int
         :param output_file: File to write captured data to
         :type output_file: typing.BinaryIO

         """
        if host is None:
            host = socket.gethostname()

        server_socket = socket.socket()
        server_socket.bind((host, port))
        server_socket.listen(2)
        conn, address = server_socket.accept()

        (remote_host, remote_port) = address

        if remote_host == '192.168.1.3':
            self.syslog_trailer = b'\n'

        last = b''

        while True:
            block = conn.recv(self.buffer_size)

            # write to capture file, if desired
            if block and output_file is not None:
                output_file.write(block)

            # Find our trailer (syslog record seperator) if
            # We haven't already.

            if self.syslog_trailer is None:
                self.syslog_trailer = self.discover_trailer(block)
                if self.syslog_trailer is None:
                    self.processor.dispatch_event(
                        ErrorEvent(
                            'Cannot locate structured data in raw block'))
                    return

            data = last + block
            if not data:
                break
            last = self._handle_records(data)

    def discover_trailer(self, block):
        structured_data = SyslogRecord.sdata_from_raw(block)
        try:
            trailer = self.trailer_discovery_method(structured_data)
            if trailer:
                log.debug(f'Trailer discovery method returned {repr(trailer)}'
                          f'. Using it')
                return trailer
        except Exception as e:
            log.error('Trailer discovery method raised exception')
            log.exception(e)

        log.debug(f'Using default trailer of {repr(DEFAULT_SYSLOG_TRAILER)}')
        # Default trailer
        return DEFAULT_SYSLOG_TRAILER

    def _handle_records(self, data):

        while True:
            pos = data.find(self.syslog_trailer)
            if pos == -1:
                return data
            self._process_record(data[0:pos])
            data = data[pos + 1:]

    def _process_record(self, data):
        record = SyslogRecord(data)
        if not record.error:
            for module in self.modules:
                module.process_record(record)
        else:
            self.processor.dispatch_event(
                ErrorEvent(
                    'Error processing record',
                    data=data))


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
            r'(?P<hostname>.+?) (?P<appname>.+?) (?P<proc_id>.+?) '
            r'(?P<msg_id>.+?) (?P<rest>.+)')

    @staticmethod
    def sdata_from_raw(block):
        """Finds the first occurrence of structured data in a raw data block.

        Returns a dict representation of the structured data.
        This is used only for syslog trailer discovery.

        """

        decoded = block.decode('utf-8')
        m = re.match(SyslogRecord.main_regex, decoded)
        if m:
            try:
                _, structured_data = SyslogRecord._parse_sdata(m.group('rest'))
                return structured_data
            except ParserError:
                pass
        return {}

    def __init__(self, record):

        self.original_record = record
        self.record_length = len(record)
        self.error = None

        # todo This needs to be handled better

        pos = record.find(b'\xef\xbb\xbf')

        if pos >= 0:
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
        self.proc_id = self.m.group('proc_id')
        self.msg_id = self.m.group('msg_id')

        try:
            self.detail, self.structured_data = self._parse_sdata(
                self.m.group('rest'))
        except ParserError as e:
            self.error = f'Cannot parse structured data: {e}'
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
                            f'SD-DATA {dataline} parse failed ')
                    else:
                        return dataline.lstrip(), parsed_struc
                element_id = m.group(1)
                dataline = m.group(2)
                state = 2
                continue
            elif state == 2:
                m = re.match(r'](.*)', dataline)
                if m:
                    dataline = m.group(1)
                    state = 1
                    continue
                m = re.match(r'(.+?)="([^"]*)"\s*(.*)', dataline)

                if m:
                    add_param(element_id, m.group(1), m.group(2))
                    has_structured_data = True
                    dataline = m.group(3)
                    continue
                else:
                    raise ParserError(
                        f'SD-DATA Key/Value {dataline} parse failed')

    def __repr__(self):
        # why?
        return f'{self.m.groupdict()} ({self.structured_data})'

    def __str__(self):
        return f'{self.hostname} {self.appname} {self.proc_id} {self.detail}'

    def __len__(self):
        return self.record_length

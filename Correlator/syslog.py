import iso8601
import logging
import re
import select
import socket
import pickle

from dataclasses import dataclass
from datetime import datetime
from mako.template import Template
from time import time, sleep
from typing import List, BinaryIO, Callable

from Correlator.event import EventProcessor, ErrorEvent, AuditEvent
from Correlator.util import ParserError, Module, GlobalConfig

DEFAULT_SYSLOG_TRAILER = b'\n'

DEFAULT_ACCEPT_HEARTBEAT_INTERVAL = 5     # 5 seconds
ACCEPT_HEARTBEAT_INTERVAL_PARAM = 'syslog_server.accept_heartbeat_interval'

DEFAULT_RECV_HEARTBEAT_INTERVAL = 5     # 5 seconds
RECV_HEARTBEAT_INTERVAL_PARAM = 'syslog_server.recv_heartbeat_interval'

DEFAULT_SAVE_STATE_INTERVAL = 5     # 5 seconds
SAVE_STATE_INTERVAL_PARAM = 'syslog_server.save_state_param'

# This must be big enough to hold enough of a syslog record to guarantee that
# it contains the entire structured data field for trailer discovery.

DEFAULT_BUFFER_SIZE = 4096

log = logging.getLogger(__name__)


@dataclass
class RawSyslogRecord:
    timestamp: str
    priority: str
    hostname: str
    appname: str
    proc_id: str
    msg_id: str
    structured_data: dict


class SyslogServer:
    """ Read and process syslog records.

    Reads from either the network or a capture file. Also handles
    writing data read from the network to a capture file, if desired.

    Args:
        modules: List of Correlator modules in this stack
        processor: Instance of EventProcessor with registered event handlers
        discovery_method: Callable that can help determine the syslog trailer
        record_filter:  Record filter list

    """
    def __init__(self, modules: List[Module], processor: EventProcessor,
                 discovery_method: Callable[[RawSyslogRecord], bytes] = None,
                 record_filter=None, state_file=None):

        self.modules = modules
        self.processor = processor
        self.buffer_size: int = DEFAULT_BUFFER_SIZE
        self.syslog_trailer = None
        self.trailer_discovery_method = discovery_method
        self.bind_retry = 1
        self.record_num = 0
        self.record_filter = record_filter
        self.output_file = None
        self.state_file = state_file
        self.all_state = {}
        self.state_timestamp = None

        if state_file is not None:
            self.load_state()

        for module in modules:
            module.event_processor = processor
            if module.module_name not in self.all_state:
                self.all_state[module.module_name] = {}
            module.init_state(self.all_state[module.module_name])

        self.accept_heartbeat_interval = GlobalConfig.get(
            ACCEPT_HEARTBEAT_INTERVAL_PARAM, DEFAULT_ACCEPT_HEARTBEAT_INTERVAL)
        self.recv_heartbeat_interval = GlobalConfig.get(
            RECV_HEARTBEAT_INTERVAL_PARAM, DEFAULT_RECV_HEARTBEAT_INTERVAL)
        self.save_state_interval = GlobalConfig.get(
            SAVE_STATE_INTERVAL_PARAM, DEFAULT_SAVE_STATE_INTERVAL)

    def debug_dump_state(self):
        print(self.all_state)

    def save_state(self):

        if not self.state_file:
            log.info('Save state: Persistence not enabled')
            return

        with open(self.state_file, 'wb') as output_file:
            pickle.dump(self.all_state, output_file, pickle.HIGHEST_PROTOCOL)
            log.info(f'Save state: state written to {self.state_file}')
            self.state_timestamp = datetime.now()

    def load_state(self):
        if not self.state_file:
            log.info("Load state: Persistence not enabled.")
            return

        try:
            with open(self.state_file, 'rb') as input_file:
                self.all_state = pickle.load(input_file)
                log.info(f'Load state: State loaded from file '
                         f'{self.state_file}.')
        except FileNotFoundError:
            log.info(
                f'Load state: State file {self.state_file} does not exist. '
                f'Initializing new state')

    def from_file(self, input_file: BinaryIO, output_file: BinaryIO = None):
        """ Processes saved syslog data from a file

        The main purpose of this method is to take a capture file as input
        rather than reading from the network. This does however, also have
        the capability to write to a file. Combined with the record_filter
        argument, this makes the way for utilities to create a new file
        from a subset of an old one.

        Args:
            input_file: File object of readable binary file
            output_file: File object of writable binary file

        """

        last = b''
        self.output_file = output_file

        while True:
            block = input_file.read(self.buffer_size)

            # Determine the trailer (syslog record seperator) if
            # we haven't already.

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

    def _heartbeat(self, message):
        log.debug(f'Heartbeat: {message}')
        for module in self.modules:
            module.process_record(None)

    def listen_single(self, host: str = None,
                      port: int = 514,
                      output_file: BinaryIO = None):

        """ Run a single thread TCP network listener and process syslog records

        This method will listen for and accept a connection, and then process
        records as they are received, forever.

        If a file object of binary file open for writing is provided in
        output_file, received packets will also be written to this file.

        Args:
            host:   host to listen on (valid AF_INET host) or None for default
            port:   port to listen on (valid AF_INET port)
            output_file:  Binary file open for writing to save received data

         """
        if host is None:
            host = socket.gethostname()

        server_socket = socket.socket()

        while True:
            try:
                server_socket.bind((host, port))
                break
            except OSError as e:
                if e.strerror.lower() == 'address already in use':
                    log.error(f'Address {host}:{port} already in use. Will '
                              f'retry in {self.bind_retry} second(s)')
                    sleep(self.bind_retry)
                else:
                    raise

        server_socket.listen(1)
        server_socket.setblocking(False)
        log.info(f'Server listening on {host}:{port}')

        # Don't block on accept forever - process heartbeats

        while True:
            readable, writable, errored = select.select(
                [server_socket], [], [], self.accept_heartbeat_interval)
            if not readable:
                self._heartbeat('Waiting for connection establishment')
                continue
            else:
                conn, (remote_host, remote_port) = server_socket.accept()
                log.info(f'Connection from: {remote_host}:{remote_port}')
                break

        last = b''

        self.output_file = output_file
        self.save_state()

        while True:
            # Nonblocking reads, for the same reason.
            readable, writable, errored = select.select(
                [conn], [], [], self.recv_heartbeat_interval)

            # Check to see if we need to save state

            seconds_delta = (
                    datetime.now() - self.state_timestamp).total_seconds()

            if seconds_delta > self.save_state_interval:
                self.save_state()

            if not readable:
                self._heartbeat('Waiting for data')
                continue
            block = conn.recv(self.buffer_size)

            if not block:
                log.error("read block evaluated false")
                break

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
        raw_block = SyslogRecord.decode_from_raw(block)
        if callable(self.trailer_discovery_method):
            try:
                trailer = self.trailer_discovery_method(raw_block)
                if trailer:
                    log.debug(f'Trailer discovery method returned '
                              f'{repr(trailer)}. Using it')
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

        if self.output_file is not None:
            # Write record to capture file
            process_record = True
            if self.record_filter is not None:
                # Unless were supplied a record_filter, and this record is
                # not to be written.
                process_record = self.record_filter[self.record_num]
            if process_record:
                self.output_file.write(data + self.syslog_trailer)

        self.record_num += 1
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
    def decode_from_raw(block):
        """Parses the data-only* portion of a syslog record in a raw data block.

        This is used to parse the first block to be used for syslog trailer
        discovery.

        * data-only means all properties up to but not including detail.

        """

        decoded = block.decode('utf-8')
        m = re.match(SyslogRecord.main_regex, decoded)
        if not m:
            return None

        try:
            _, structured_data = SyslogRecord._parse_sdata(m.group('rest'))
        except ParserError:
            structured_data = {}

        return RawSyslogRecord(
            timestamp=m.group('timestamp_str'),
            priority=m.group('priority'),
            hostname=m.group('hostname'),
            appname=m.group('appname'),
            proc_id=m.group('proc_id'),
            msg_id=m.group('msg_id'),
            structured_data=structured_data
        )

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
            timestamp_tz = iso8601.parse_date(self.timestamp_str)
        except iso8601.ParseError:
            self.error = 'Cannot parse timestamp'
            return

        self.timestamp = timestamp_tz.replace(tzinfo=None)

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
        # todo: why?
        return f'{self.m.groupdict()} ({self.structured_data})'

    def __str__(self):
        return (f'{self.timestamp.strftime("%Y-%m-%d %H:%M:%S")}: '
                f'{self.hostname} {self.appname} {self.proc_id} {self.detail}')

    def __len__(self):
        return self.record_length

import iso8601
import logging
import pickle
import re
import select
import socket
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, BinaryIO, Callable

from Correlator.config_store import ConfigType, RuntimeConfig
from Correlator.Event.core import EventProcessor, Event, StatsEvent, SimpleError
from Correlator.util import ParserError, Module


log = logging.getLogger(__name__)

SyslogConfig = [
    {
        'save_store_interval': {
            'default': 5,
            'desc': 'Time in minutes in between saves of the persistence store',
            'type': ConfigType.INTEGER
        }
    },
    {
        'buffer_size': {
            'default': 4096,
            'desc': 'Read buffer size. This must be large enough so that an '
                    'entire header and structured data can fit.',
            'type': ConfigType.INTEGER
        }
    },
    {
        'default_trailer': {
            'default': '\n',
            'desc': 'The default syslog record separator to use if trailer '
                    'discovery can\'t conclusively determine the record '
                    'separator in use',
            'type': ConfigType.STRING
        }
    },
    {
        'listen_address': {
            'default': '0.0.0.0',
            'desc': 'The IPv4 address of the interface to listen on. 0.0.0.0 '
                    'means listen on all interfaces.',
            'type': ConfigType.STRING
        }
    },
    {
        'listen_port': {
            'default': 514,
            'desc': 'The TCP port number to listen on.',
            'type': ConfigType.INTEGER
        }
    }

]


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

                # if not has_structured_data and dataline[0:2] == '- ':
                #     return dataline[2:], {}

                if not has_structured_data:
                    m = re.match(r'-\s+(.+)', dataline)
                    if m:
                        return m.group(1), {}

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


@dataclass
class RawSyslogRecord:
    timestamp: str
    priority: str
    hostname: str
    appname: str
    proc_id: str
    msg_id: str
    structured_data: dict


# module_name = 'syslog_server'


class SyslogServer:

    """ Read and process syslog records from the network, or file.

    Can also write records to a capture file for later replay.

    Args:
        modules: List of Correlator modules in this stack
        processor: Instance of EventProcessor with registered event handlers
        discovery_method: Callable that can help determine the syslog trailer
        record_filter:  Record filter list
        store_file: Name of file to read and write the persistence store
        record: Custom record class to use (i.e. subclass of SyslogRecord)

    """

    ConfigModuleName = 'syslog_server'      # For Runtime configuration
    RuntimeConfig.add(SyslogConfig, ConfigModuleName)

    def __init__(self, modules: List[Module], processor: EventProcessor,
                 discovery_method: Callable[[RawSyslogRecord], bytes] = None,
                 record_filter=None, store_file: str = None,
                 record: type = SyslogRecord):

        self.modules = modules
        self.processor = processor
        self.syslog_trailer = None
        self.trailer_discovery_method = discovery_method
        self.record_num = 0
        self.record_filter = record_filter
        self.output_file = None
        self.store_file: str = store_file
        self.skip_save_store = False
        self.full_store = {}
        self.store_timestamp = None
        self.last_tick = None
        self.record = record

        if store_file is not None:
            self.load_store()

        for module in modules:
            module.event_processor = processor
            if module.module_name not in self.full_store:
                self.full_store[module.module_name] = module.model()
            module.store = self.full_store[module.module_name]
            module.post_init_store()

        self.save_store_interval = RuntimeConfig.get(
            f'{self.ConfigModuleName}.save_store_interval')
        self.buffer_size = RuntimeConfig.get(f'{self.ConfigModuleName}.buffer_size')

        self.default_syslog_trailer = RuntimeConfig.get(
            f'{self.ConfigModuleName}.default_trailer').encode('utf-8')

    def debug_dump_store(self):
        log.debug(repr(self.full_store))

    def save_store(self):

        if self.skip_save_store:
            return

        if not self.store_file:
            log.info('Save store: Persistence not enabled')
            self.skip_save_store = True
            return

        with open(self.store_file, 'wb') as output_file:
            pickle.dump(self.full_store, output_file, pickle.HIGHEST_PROTOCOL)
            log.info(f'Save store: store written to {self.store_file} and is {output_file.tell()} bytes')

    def load_store(self):
        if not self.store_file:
            log.info("Load store: Persistence not enabled.")
            return

        try:
            with open(self.store_file, 'rb') as input_file:
                self.full_store = pickle.load(input_file)
                log.info(f'Load store: Store loaded from file '
                         f'{self.store_file}.')
        except FileNotFoundError:
            log.info(
                f'Load store: Store file {self.store_file} does not exist. '
                f'Initializing new store')

    def from_file(self, input_file: BinaryIO, output_file: BinaryIO = None):
        """ Processes saved syslog data from a capture file rather than network

        Also supports writing to a capture file. Combined with the record_filter
        argument in the constructor, this provides rudimentary functionality to
        edit capture files by reading from one and writing to another, while
        stripping som packets.

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
                        SimpleError(
                            {'message': 'Problem running trailer discovery'}))
                    return

            data = last + block
            if not data:
                return
            last = self._process_block(data)

    def handle_connection(self, host, port, output_file: BinaryIO = None):

        server_socket = socket.socket()
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((host, port))

        server_socket.listen(1)
        server_socket.setblocking(False)

        log.info(f'Server listening on {host}:{port}')

        self.last_tick = datetime.now()

        while True:
            timeout = self._seconds_remaining()
            readable, writable, errored = select.select(
                [server_socket], [], [], timeout)

            now = datetime.now()

            if not readable:
                # Always tick if we time out, chances are we are at a boundary
                self._tick(now)
                continue

            if self.last_tick.minute != now.minute:
                self._tick(now)

            conn, (remote_host, remote_port) = server_socket.accept()
            log.info(f'Connection from: {remote_host}:{remote_port}')
            break

        last = b''

        self.output_file = output_file

        while True:
            timeout = self._seconds_remaining()
            # Nonblocking reads, for the same reason.
            readable, writable, errored = select.select(
                [conn], [], [], timeout)

            now = datetime.now()
            if self.last_tick.minute != now.minute:
                self._tick(now)

            if not readable:
                continue

            # Otherwise, read

            block = conn.recv(self.buffer_size)

            if not block:
                log.debug("read block evaluated false")
                break

            # Determine the syslog trailer (record separator) if we haven't
            # already

            if self.syslog_trailer is None:
                self.syslog_trailer = self.discover_trailer(block)
                if self.syslog_trailer is None:
                    self.processor.dispatch_event(
                        SimpleError({
                            'message': 'Cannot locate structured data in raw block'
                        }))
                    return

            # Combine this new block with whatever was left from the last block
            # (if any), and process any complete syslog records within it

            data = last + block

            if not data:
                # no data to proces, all done
                break

            last = self._process_block(data)

    def listen_single(self, output_file: BinaryIO = None):

        """ Run a single thread TCP network listener and process syslog records

        This method will listen for and accept a connection, and then process
        records as they are received, forever.

        If a file object of binary file open for writing is provided in
        output_file, received packets will also be written to this file.

        Args:
            output_file:  Binary file open for writing to save received data

         """

        host = RuntimeConfig.get(f'{self.ConfigModuleName}.listen_address')
        port = RuntimeConfig.get(f'{self.ConfigModuleName}.listen_port')

        # todo: Why?

        if host is None:
            host = socket.gethostname()
        # GlobalConfig.debug_log()

        while True:
            try:
                self.handle_connection(host, port, output_file)
            except KeyboardInterrupt:
                self.save_store()
                break


    @staticmethod
    def _seconds_remaining():
        """Calculate the number of seconds until the minute rolls over"""

        now = datetime.now()

        then = (now + timedelta(minutes=1)).replace(second=0)
        value = (then-now).seconds

        return value

    def _tick(self, now: datetime):
        """Processes a tick of the clock.

        If a minute boundary is crossed, it performs its per-minute
        tasks:

        - Determine if it's time to save store
        - Run any appropriate task handlers if they were defined by the module

        This is meant to be called at the top of every minute.

        """

        # Check to make sure its necessary. This makes it zero risk to be run
        # from anywhere, even if it may have been called already for this
        # minute.

        last_minute = int(self.last_tick.timestamp() / 60)
        this_minute = int(now.timestamp() / 60)

        if this_minute == last_minute:
            log.debug('Tick called within the same minute. Ignoring.')
            return

        self.last_tick = now

        # check to see if it's time to save the persistence store

        if now.minute % self.save_store_interval == 0:
            self.save_store()

        # Setup array of actions that are valid for this minute

        actions = [
            [True, 'timer_handler_minute'],
            [True, f'timer_handler_{now.hour}_{now.minute}'],
            [now.minute % 5 == 0, 'timer_handler_5_minutes'],
            [now.minute % 10 == 0, 'timer_handler_10_minutes'],
            [now.minute % 15 == 0, 'timer_handler_15_minutes'],
            [now.minute % 30 == 0, 'timer_handler_30_minutes'],
            [now.minute == 0,  'timer_handler_1_hour'],

        ]

        # Go through the modules and call the handlers if they are defined

        for module in self.modules:
            for (flag, method) in actions:
                if flag:
                    handler = getattr(module, method, None)
                    if callable(handler):
                        handler(now)

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

        log.debug(
            f'Using default trailer of {repr(self.default_syslog_trailer)}')
        # Default trailer
        return self.default_syslog_trailer

    def _process_block(self, data):

        while True:
            pos = data.find(self.syslog_trailer)
            if pos == -1:
                return data
            self._process_record(data[0:pos])
            data = data[pos + 1:]

    def _process_record(self, data):
        record = self.record(data)

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
                module.handle_record(record)
        else:
            self.processor.dispatch_event(
                SimpleError({'message': 'Error processing record'}))


class SyslogStatsEvent(StatsEvent):

    schema = [
        ['start', 'Session started:'],
        ['end', 'Session ended:'],
        ['duration', 'Session duration:'],
    ]
    templates = {
        'text/plain': {
            'summary': 'Statistics: Session started at ${start}, ended at ${end}, with a duration of ${duration}'
        },
        'text/html': {
            'summary': 'Statistics: Session started at <strong>${start}</strong>, ended at <strong>${end}</strong>, with a duration of <strong>${duration}</strong>'
        }

    }

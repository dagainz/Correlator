import argparse
import frontend_record_pb2_grpc
import frontend_record_pb2
import grpc
import iso8601
import logging
import os
import re
import select
import socket
import time
from dataclasses import dataclass
from typing import Callable

from Correlator.app_config import ApplicationConfig

from Correlator.config_store import ConfigType, RuntimeConfig
from Correlator.core import setup_root_logger, RecordTypes, ResultCodes, Instance

log = logging.getLogger(__name__)

SyslogSourceConfig = [
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
    },
    {
        'grpc_host': {
            'default': '0.0.0.0',
            'desc': 'The address of the Correlator input processor',
            'type': ConfigType.STRING
        }
    },
    {
        'grpc_port': {
            'default': 50051,
            'desc': 'The TCP port of the Correlator input processor',
            'type': ConfigType.INTEGER
        }
    },
    {
        'tenant': {
            'default': '',
            'desc': 'The tenant associated with this connector instance',
            'type': ConfigType.STRING
        }
    }

]


class SyslogException(Exception):
    pass


class ParserError(Exception):
    pass


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

        self.record_length = len(record)
        self.error = None
        self.record = record

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

    def raw(self):
        return self.record


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

    """ Read and process syslog records from the network.

    Args:
        discovery_method: Callable that can help determine the syslog trailer

    """

    def __init__(self, tenant_id: str, source_id: str,
                 discovery_method: Callable[[RawSyslogRecord], bytes] = None):

        self.syslog_trailer = None
        self.trailer_discovery_method = discovery_method
        self.record_num = 0
        self.last_tick = None

        self.config_prefix = f'sources.{source_id}'

        self.default_syslog_trailer = RuntimeConfig.get(
            f'{self.config_prefix}.default_trailer').encode('utf-8')

        self.buffer_size = RuntimeConfig.get(
            f'{self.config_prefix}.buffer_size')

        self.listen_address = RuntimeConfig.get(
            f'{self.config_prefix}.listen_address')

        self.listen_port = RuntimeConfig.get(
            f'{self.config_prefix}.listen_port')

        self.tenant_id = tenant_id
        self.source_id = source_id

        self.timeout_seconds = 60
        self.server_socket = None

    # def _heartbeat(self):
    #     log.info(f"Heartbeat! {self.timeout_seconds}")

    def _heartbeat_message(self):
        return frontend_record_pb2.Record(
            tenant_id=self.tenant_id,
            timestamp=int(time.time() * 1000),
            type=RecordTypes.HEARTBEAT.value,  # Heartbeat
            source_id=self.source_id,
            raw_data=b''
        )

    def _data_message(self, record):
        return frontend_record_pb2.Record(
            tenant_id=self.tenant_id,
            timestamp=int(time.time() * 1000),
            type=RecordTypes.SYSLOG_DATA.value,  # Syslog
            source_id=self.source_id,
            raw_data=record.raw()
        )

    def __iter__(self):

        timeout = self.timeout_seconds

        while True:

            self.server_socket = socket.socket()
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.listen_address, self.listen_port))

            self.server_socket.listen(1)
            self.server_socket.setblocking(False)

            log.info(f'Server waiting on {self.listen_address}:{self.listen_port}')

            while True:
                # log.debug("Waiting for connection")
                readable, writable, errored = select.select(
                    [self.server_socket], [], [], timeout)

                if not readable:
                    # Timed-out, send heartbeat
                    yield self._heartbeat_message()
                    continue
                conn, (remote_host, remote_port) = self.server_socket.accept()
                log.info(f'Connection from: {remote_host}:{remote_port}')
                break

            last = b''

            while True:
                # timeout = self._seconds_remaining()
                # Nonblocking reads, for the same reason.
                readable, writable, errored = select.select(
                    [conn], [], [], self.timeout_seconds)

                if not readable:
                    log.debug('Timed out waiting for data')
                    # timed-out
                    yield self._heartbeat_message()
                    continue

                block = conn.recv(self.buffer_size)

                if not block:
                    log.info('Remote closed connection')
                    conn.close()
                    self.server_socket.close()
                    break

                # Determine the syslog trailer (record separator) if we haven't
                # already

                if self.syslog_trailer is None:
                    self.syslog_trailer = self.discover_trailer(block)
                    if self.syslog_trailer is None:
                        raise SyslogException('Parse: Can\'t find structured data')

                # Combine this new block with whatever was left from the last block
                # (if any), and process any complete syslog records within it

                data = last + block

                if not data:
                    # no data to proces, all done
                    break

                while True:
                    pos = data.find(self.syslog_trailer)
                    if pos == -1:
                        last = data
                        break
                    else:
                        record = SyslogRecord(data[0:pos])
                        if not record.error:
                            log.info('Successfully processed syslog record')
                            yield self._data_message(record)
                        else:
                            log.error('syslog parse error')

                    data = data[pos + 1:]

#                last = self._process_block(data)

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


class CLI:

    def __init__(self):
        self.log = log.getChild('tcp_syslog')

        parser = argparse.ArgumentParser(description='Syslog Server Correlator source.')
        parser.add_argument('--id', required=True, help='Source ID')
        parser.add_argument(
            '--config_file',
            required=True,
            help='Configuration file to use'
        )
        parser.add_argument('-d', '--debug', action='store_true', help='Enable more verbose output')

        args = parser.parse_args()

        if 'CORRELATOR_CFG' in os.environ:
            final_config_file = os.environ['CORRELATOR_CFG']
            self.log.debug(f'CORRELATOR_CFG environment variable set. Using its'
                           f' value of  {final_config_file}')
        else:
            final_config_file = args.config_file
            self.log.debug(f'CORRELATOR_CFG environment variable not set.'
                           f' Using the preset value of {final_config_file}')

        if not ApplicationConfig.load(final_config_file):
            raise ValueError('Cannot load configuration file')

        cfgblock = ApplicationConfig.source_by_id(args.id)

        if not cfgblock:
            raise ValueError(f'No source with ID {args.id} found in configuration')

        if args.debug:
            level = logging.DEBUG
        else:
            level = logging.INFO

        setup_root_logger(level)

        configuration_prefix = f"sources.{args.id}"

        RuntimeConfig.add(SyslogSourceConfig, configuration_prefix)

        ApplicationConfig.process_source_config(args.id)
        try:
            hostname = RuntimeConfig.get(f"{configuration_prefix}.grpc_host")
            port = RuntimeConfig.get(f"{configuration_prefix}.grpc_port")
            tenant = RuntimeConfig.get(f"{configuration_prefix}.tenant")
        except ValueError as e:
            log.error(f'Invalid configuration: {e}')
            return

        log.info(f'Correlator {Instance.Version} Source ID {args.id} TCP Syslog server for tenant {tenant} startup')

        log.debug(f'Connecting to input processor at {hostname}:{port} via gRPC ')
        with grpc.insecure_channel(f'{hostname}:{port}') as channel:
            log.info(f'gRPC connection established to Correlator input processor at {hostname}:{port}')
            SyslogSource = SyslogServer(source_id=args.id, tenant_id=tenant)
            stub = frontend_record_pb2_grpc.FrontEndInputStub(channel)
            response = stub.ProcessRecord(iter(SyslogSource))
            message = f'Server responded with {response.message}, Code: {response.code}'
            if response.code != 0:
                log.error(message)
            else:
                log.info(message)


if __name__ == '__main__':
    CLI()

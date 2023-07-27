import argparse
import logging
import os
import sys
from datetime import datetime

from Correlator.config import SystemConfig
from Correlator.global_config import GlobalConfig, ConfigException
from Correlator.Event.core import EventProcessor, EventType, EventStatus
from Correlator.syslog import (RawSyslogRecord, SyslogRecord, SyslogServer,
                               SyslogStatsEvent)
from Correlator.util import (setup_root_logger, capture_filename,
                             format_timestamp, Module)

log = logging.getLogger(__name__)


class BaseCLI:
    @staticmethod
    def syslog_record_model():
        return SyslogRecord

    @staticmethod
    def trailer_discovery_method(
            raw_record: RawSyslogRecord) -> bytes | None:
        return None

    def __init__(self):

        parser = argparse.ArgumentParser(
            'Correlator syslog server CLI',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=__doc__)

        parser.add_argument(
            '--d',
            help='Debug level', action='store_true'
        )
        parser.add_argument(
            '--config_file',
            help='Configuration file to use',
            default='/Users/timp/Projects/Correlator/config.json'
        )
        parser.add_argument(
            '--app',
            help='Application to run',
            required=True
        )

        parser.add_argument(
            '--o',
            action='append',
            metavar='option.name=value',
            help='Set Correlator option.name to value',
            default=[]
        )

        group = parser.add_mutually_exclusive_group()

        group.add_argument(
            '--write-file',
            metavar='filename', nargs='?', default='.',
            help='File to capture records and save to raw syslog capture file')

        group.add_argument(
            '--read-file',
            metavar='filename',
            help='raw syslog capture file to read and process')

        parser.add_argument(
            '--store-file',
            metavar='filename',
            help='File to save and load the persistence store '
                 'from')

        parser.add_argument(
            '--config',
            action='store_true',
            help='*ONLY* show the valid configuration options and their values '
                 'then exit'
        )

        cmd_args = parser.parse_args()

        # Setup logging

        debug_level = logging.DEBUG if cmd_args.d else logging.INFO
        setup_root_logger(debug_level)

        if not SystemConfig.load(cmd_args.config_file):
            sys.exit(0)

        # Give a default value to write_file if not provided

        d = vars(cmd_args)

        if cmd_args.write_file is None:
            d['write_file'] = capture_filename()
        elif cmd_args.write_file == '.':
            d['write_file'] = None

        # Prepare list of settings from command line

        settings = []

        for option in cmd_args.o:
            pos = option.find('=')
            if pos > 0:
                key = option[0:pos]
                value = option[pos+1:]
                settings.append((key, value))

        stack = SystemConfig.build_stack(cmd_args.app, settings)
        if stack is None:
            log.error('Can\'t initialize application. Exiting')
            sys.exit(0)
        # Check if creds required for any event handlers

        ids = stack.processor.check_creds()

        if ids:
            for userid in ids:
                log.error(f'A password for id {userid} was not found in the credential store')
            log.info('Shutting down due to missing passwords')
            sys.exit(0)

        # Prepare output file, if using

        output_file = None

        if cmd_args.write_file:
            if os.path.exists(cmd_args.write_file):
                print(f'{cmd_args.write_file} exists. Delete it first')
                sys.exit(0)
            else:
                log.info(f'Writing received syslog data to capture file '
                         f'{cmd_args.write_file}')
                output_file = open(cmd_args.write_file, 'wb')

        if cmd_args.config:
            GlobalConfig.dump_to_log(debug=False)
            log.info('Shutting down after configuration query')
            sys.exit(0)
        else:
            GlobalConfig.dump_to_log()

        server = SyslogServer(stack.modules,
                              stack.processor,
                              record=self.syslog_record_model(),
                              store_file=cmd_args.store_file,
                              discovery_method=self.trailer_discovery_method)

        start = datetime.now()

        if cmd_args.read_file:
            # Replay from capture file
            log.info(f'Reading from capture file {cmd_args.read_file}')
            server.from_file(open(cmd_args.read_file, 'rb'))

        else:
            server.listen_single(output_file=output_file)

        end = datetime.now()

        for module in stack.modules:
            module.statistics()

        e = SyslogStatsEvent(
            {
                'start': format_timestamp(start),
                'end': format_timestamp(end),
                'duration': str(end - start)
            })
        e.system = 'syslog-server'
        stack.processor.dispatch_event(e)


if __name__ == '__main__':
    BaseCLI()

import argparse
import logging
import os
import sys
from datetime import datetime

from Correlator.stack import SystemConfig
from Correlator.global_config import GlobalConfig, ConfigException
from Correlator.Event.core import EventProcessor, EventType, EventStatus
from Correlator.syslog import (RawSyslogRecord, SyslogRecord, SyslogServer,
                               SyslogStatsEvent)
from Correlator.util import (setup_root_logger, capture_filename,
                             format_timestamp, Module)

# log = logging.getLogger(__name__)


class SyslogServerCLI:

    cli_title = 'Correlator syslog server'
    default_config_file = '/Users/timp/Projects/Correlator/config.json'

    @staticmethod
    def syslog_record_model():
        return SyslogRecord

    @staticmethod
    def trailer_discovery_method(
            raw_record: RawSyslogRecord) -> bytes | None:
        return None

    def __init__(self):

        parser = argparse.ArgumentParser(
            description=self.cli_title)

        parser.add_argument(
            '--d',
            help='Debug level', action='store_true'
        )

        parser.add_argument(
            '--config_file',
            help='Configuration file to use',
            default=self.default_config_file
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

        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            '--app',
            help='Application to run'
        )
        group.add_argument(
            '--apps',
            help='List available applications',
            action='store_true'
        )
        cmd_args = parser.parse_args()

        # Setup logging

        self.log = logging.getLogger('syslog_server')

        debug_level = logging.DEBUG if cmd_args.d else logging.INFO
        setup_root_logger(debug_level)

        self.log.info('Starting up with command line arguments: ' + " ".join(
            sys.argv[1:]))

        if not SystemConfig.load(cmd_args.config_file):
            sys.exit(0)

        # If we are just listing apps, do it

        if cmd_args.apps:
            self.log.info(f'{"Application":<25} Description')
            self.log.info(f'{"-----------":<25} -----------')
            for (app, desc) in SystemConfig.apps():
                self.log.info(f'{app:<25} {desc}')
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
            self.log.error('Can\'t initialize application. Exiting')
            sys.exit(0)

        # Check if creds required for any modules or event handlers

        ids = stack.processor.check_creds()

        if ids:
            for userid in ids:
                self.log.error(f'A password for id {userid} was not found in the '
                          f'credential store')
            self.log.info('Shutting down due to missing secrets')
            sys.exit(0)

        # Prepare output file, if using

        output_file = None

        if cmd_args.write_file:
            if os.path.exists(cmd_args.write_file):
                print(f'{cmd_args.write_file} exists. Delete it first')
                sys.exit(0)
            else:
                self.log.info(f'Writing received syslog data to capture file '
                         f'{cmd_args.write_file}')
                output_file = open(cmd_args.write_file, 'wb')

        if cmd_args.config:
            GlobalConfig.dump_to_log(debug=False)
            self.log.info('Shutting down after configuration query')
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
            self.log.info(f'Reading from capture file {cmd_args.read_file}')
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


# Setuptools entrypoint

def cli():
    SyslogServerCLI()


# For -m or running/debugging in IDE

if __name__ == '__main__':
    SyslogServerCLI()


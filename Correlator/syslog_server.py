import argparse
import logging
import os
import sys
from datetime import datetime

from Correlator.config_store import RuntimeConfig
from Correlator.app_config import ApplicationConfig
from Correlator.Event.core import EventProcessor, EventSeverity
from Correlator.syslog import (RawSyslogRecord, SyslogRecord, SyslogServer,
                               SyslogStatsEvent)
from Correlator.core import (setup_root_logger, capture_filename, Instance,
                             format_timestamp, prefix_run_dir, setup_keyring)


class SyslogServerCLI:

    cli_title = 'Correlator syslog server'
    default_config_file = '/usr/src/app/config.json'

    @staticmethod
    def syslog_record_model():
        return SyslogRecord

    @staticmethod
    def trailer_discovery_method(
            raw_record: RawSyslogRecord) -> bytes | None:
        return None

    def quit(self, error_message=None):
        if error_message:
            self.log.error(error_message)
        self.log.info('Shutting down')
        sys.exit(0)

    def start(self):
        self.log.info(f'Correlator version {Instance.Version} starting with '
                      f'command line arguments: {" ".join(sys.argv[1:])}')

    def __init__(self):

        parser = argparse.ArgumentParser(
            description=self.cli_title)

        parser.add_argument(
            '--pydebug',
            help='Debug using PyCharm debug server', action='store_true'
        )
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
            '--option',
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

        self.start()

        setup_keyring()

        # Enable remote pycharm logging

        if cmd_args.pydebug:
            self.python_port = None

            self.log.info('Configuring PyCharm remote debugging')

            try:
                self.python_port = os.environ['PYCHARM_DEBUG_PORT']
                self.python_host = os.environ['PYCHARM_DEBUG_HOST']
            except KeyError as e:
                self.quit(f'{e} environment variable is not set')

            try:
                self.python_port = int(self.python_port)
            except ValueError:
                self.quit('PYCHARM_DEBUG_PORT environment variable must be an '
                          'integer')

            self.log.debug(f'PyCharm remote debugging destination: '
                           f'{self.python_host}:{self.python_port}')

            try:
                import pydevd_pycharm
                pydevd_pycharm.settrace(
                    self.python_host,
                    port=self.python_port,
                    stdoutToServer=True,
                    stderrToServer=True)

            except ConnectionRefusedError:
                self.quit(f'Connection to the PyCharm debug server '
                          f'{self.python_host}:{self.python_port} refused')

            except ModuleNotFoundError:
                self.quit('Can\'t find module named pydevd_pycharm')

        if 'CORRELATOR_CFG' in os.environ:
            final_config_file = os.environ['CORRELATOR_CFG']
            self.log.debug(f'CORRELATOR_CFG environment variable set. Using its'
                           f' value of  {final_config_file}')
        else:
            final_config_file = cmd_args.config_file
            self.log.debug(f'CORRELATOR_CFG environment variable not set.'
                           f' Using the preset value of {final_config_file}')

        if not ApplicationConfig.load(final_config_file):
            self.quit()

        # If we are just listing apps, do it

        if cmd_args.apps:
            self.log.info(f'{"Application":<25} Description')
            self.log.info(f'{"-----------":<25} -----------')
            for (app, desc) in ApplicationConfig.apps():
                self.log.info(f'{app:<25} {desc}')
            self.quit()

        # Give a default value to write_file if not provided

        d = vars(cmd_args)

        if cmd_args.write_file is None:
            d['write_file'] = capture_filename()
        elif cmd_args.write_file == '.':
            d['write_file'] = None

        # Prepare list of settings from command line

        settings = []

        for option in cmd_args.option:
            pos = option.find('=')
            if pos > 0:
                key = option[0:pos]
                value = option[pos+1:]
                settings.append((key, value))

        stack = ApplicationConfig.build_stack(cmd_args.app, settings)
        if stack is None:
            self.quit()

        run_dir = RuntimeConfig.get('system.run_dir')
        if not os.access(run_dir, os.W_OK):
            self.quit(f'Can\'t write to configured run directory {run_dir}')

        # Check if creds required for any modules or event handlers

        ids = stack.processor.check_creds()

        if ids:
            for userid in ids:
                self.log.error(
                    f'A password for id {userid} was not found in the '
                    f'credential store')
            self.quit()

        # Prepare output file, if using

        output_fd = None

        if cmd_args.write_file:
            filename = prefix_run_dir(cmd_args.write_file)

            if os.path.exists(filename):
                self.quit(f'{filename} already exists.')
            else:
                self.log.info(f'Writing received syslog data to capture file '
                              f'{filename}')
                output_fd = open(filename, 'wb')

        store_filename = None

        if cmd_args.store_file:
            store_filename = prefix_run_dir(cmd_args.store_file)

        if cmd_args.config:
            RuntimeConfig.dump_to_log(debug=False)
            self.log.info('Shutting down after configuration query')
            self.quit()
        else:
            RuntimeConfig.dump_to_log()

        server = SyslogServer(stack.modules,
                              stack.processor,
                              record=self.syslog_record_model(),
                              store_file=store_filename,
                              discovery_method=self.trailer_discovery_method)

        module_name = server.ConfigModuleName

        start = datetime.now()

        if cmd_args.read_file:
            # Replay from capture file
            self.log.info(f'Reading from capture file {cmd_args.read_file}')
            server.from_file(open(cmd_args.read_file, 'rb'))

        else:
            server.listen_single(output_file=output_fd)

        end = datetime.now()

        for module in stack.modules:
            module.statistics()

        e = SyslogStatsEvent(
            {
                'start': format_timestamp(start),
                'end': format_timestamp(end),
                'duration': str(end - start)
            })
        e.system = module_name
        stack.processor.dispatch_event(e)

        self.quit()


# Setuptools entrypoint

def cli():
    SyslogServerCLI()


# For -m or running/debugging in IDE

if __name__ == '__main__':
    SyslogServerCLI()


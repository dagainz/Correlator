""" Correlator library syslog server

Contains the functionality within the base CLI, plus:

 --sshd command line option enables the sshd-login module

"""

import argparse
from typing import List

from Correlator.Event.core import EventProcessor
from Correlator.server_common import BaseCLI
from Correlator.util import Module


class SyslogServerCLI(BaseCLI):
    def add_arguments(self, parser: argparse.ArgumentParser):
        parser.add_argument(
            '--sshd',
            action='store_true', help='Activate ssh login module')

    def modify_stack(self, cmd_args: argparse.Namespace,
                     modules: List[Module], processor: EventProcessor):

        if cmd_args.sshd:
            from Correlator.Module.sshd import SSHD
            modules.append(SSHD())


# setuptools entry_point
def cli():
    SyslogServerCLI()


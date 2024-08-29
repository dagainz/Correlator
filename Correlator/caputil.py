""" Syslog capture file command line utility

Used to dump the summaries of each saved syslog record to the console,
and create new syslog capture files from subsets of existing ones.

Usage:


# Dump a summary line for every syslog record to the console.
caputil --in capturefile.cap

# Same, but write to a file for trimming
caputil --in capturefile.cap > capturefile.txt

# Create a new capture file that contain records listed in capturefile.txt
caputil --in capturefile.cap --out newfile.cap --filter capturefile.txt


To indicate which records should be copied from the input file to the output
file, mark the undesired records in the capturefile with a hash mark (#) at
the beginning of the line.

"""

import argparse
import logging
import os
import sys

from Correlator.Event.core import EventProcessor
from Correlator.Module.report import Report
from Correlator.syslog import SyslogServer
from Correlator.util import setup_root_logger


def cli():

    parser = argparse.ArgumentParser(
        description='Correlator Syslog capture file utility',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--d', help='Debug level', action='store_true'
    )

    parser.add_argument(
        '--in',
        help='raw syslog capture file to read',
        metavar='filename',
        required=True
    )
    parser.add_argument(
        '--out',
        help='raw syslog capture file to write',
        metavar='filename'
    )
    parser.add_argument(
        '--filter',
        metavar='filename',
        help='file that list of records to include in output'
    )

    cmd_args = parser.parse_args()

    debug_level = logging.DEBUG if cmd_args.d else logging.INFO
    setup_root_logger(debug_level)
    log = logging.getLogger(__name__)

    if cmd_args.out and cmd_args.filter is None:
        parser.error('--out requires --records')

    if cmd_args.filter and cmd_args.out is None:
        parser.error('--records requires --out')

    raw_args = vars(cmd_args)

    file_in = open(raw_args["in"], 'rb')
    file_out = None
    filter_list = None

    if cmd_args.out:
        if os.path.exists(cmd_args.out):
            print(f'{cmd_args.out} exists. Delete it first')
            sys.exit(0)
        else:
            file_out = open(cmd_args.out, 'wb')
            log.info(f'Writing selected records to {cmd_args.out}')

    if cmd_args.filter:
        record_num = 0
        total_records = 0
        included_records = 0

        filter_list = []

        with open(cmd_args.filter) as r:
            for line in r:
                if line[0] == '#':
                    log.debug(f'Skipping line {line}')
                    filter_list.append(False)
                else:
                    log.debug(f'Including line {line}')
                    filter_list.append(True)
                    included_records += 1
                record_num += 1
                total_records += 1
        log.info(f'Including {included_records} records out of {total_records}')

    # Build Correlator stack
    processor = EventProcessor()
    from Correlator.Event.log import LogbackListener
    processor.register_listener(LogbackListener('Logback'))
    modules = [Report('Report')]

    server = SyslogServer(modules, processor, record_filter=filter_list)
    server.from_file(file_in, file_out)


if __name__ == '__main__':
    cli()

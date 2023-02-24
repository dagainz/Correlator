import argparse
import logging
import os
import sys
import textwrap

from Correlator.event import EventProcessor, LogbackListener
from Correlator.Module.report import Report
from Correlator.syslog import SyslogServer
from Correlator.util import setup_root_logger


def cli():

    parser = argparse.ArgumentParser(
        description='Correlator Syslog capture file utility',
        prog='caputil.py',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
        Output record summaries for all records in logfile:
        
          caputil.py --in <capfile.cap>
          
        To create a new capture file with only some original records:

          Create the filter file:   
               
            caputil.py --in <capfile.cap> > capfilter
            
          Edit the filter file:
          
            Use an editor to add a hash mark (#) to the beginning of all lines
            that you do not want in the output file.
          
          Create the new file:
          
            caputil.py --in <capfile.cap> --out <newfile.cap> --record capfilter
        """)

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
        '--records',
        metavar='filename',
        help='file that list of records to include in output (default is all)'
    )

    cmd_args = parser.parse_args()

    debug_level = logging.DEBUG if cmd_args.d else logging.INFO
    setup_root_logger(debug_level)
    log = logging.getLogger(__name__)

    if cmd_args.out and cmd_args.records is None:
        parser.error('--out requires --records')

    if cmd_args.records and cmd_args.out is None:
        parser.error('--records requires --out')

    raw_args = vars(cmd_args)

    file_in = open(raw_args["in"], 'rb')
    file_out = None
    record_list = None

    if cmd_args.out:
        if os.path.exists(cmd_args.out):
            print(f'{cmd_args.out} exists. Delete it first')
            sys.exit(0)
        else:
            file_out = open(cmd_args.out, 'wb')
            log.info(f'Writing selected records to {cmd_args.out}')

    if cmd_args.records:
        record_num = 0
        total_records = 0
        included_records = 0

        record_list = []

        with open(cmd_args.records) as r:
            for line in r:
                if line[0] == '#':
                    log.debug(f'Skipping line {line}')
                    record_list.append(False)
                else:
                    log.debug(f'Including line {line}')
                    record_list.append(True)
                    included_records += 1
                record_num += 1
                total_records += 1
        log.info(f'Including {included_records} records out of {total_records}')

    # Build Correlator stack
    processor = EventProcessor()
    processor.register_listener(LogbackListener())
    modules = [Report(processor)]

    # Read

    server = SyslogServer(modules, processor, record_filter=record_list)
    server.from_file(file_in, file_out)


if __name__ == '__main__':
    cli()

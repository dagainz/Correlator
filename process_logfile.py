#!python3

import argparse
import logging
from Frontend.logfile import LogfileProcessor
from Notify.notify import Notifiers, CSVNotify, LogbackNotify
from Module.ucpath_queue import I280Queue
from lib.util import LogHelper, build_modules

log = logging.getLogger('logger')

parser = argparse.ArgumentParser('Log analyze and report')
parser.add_argument(
    '--d', action='store_true', help='Show debugging messages"')
parser.add_argument(
    '--csv', action='store_true',
    help='Write audit data for each module to csv files')
parser.add_argument('--logfile', help='Log file to parse', required=True)
parser.add_argument('--instance', help='Instance name', required=True)
parser.add_argument('--hostname', help='Host name', required=True)

args = parser.parse_args()

# Set up the notifier chain
notifiers = Notifiers()
# Add the basic console notifier
# notifiers.add_notifier(ConsoleNotify())
notifiers.add_notifier(LogbackNotify(log))
if args.csv:
    # add the CSV notifier if requested.
    notifiers.add_notifier(CSVNotify())

# List of modules

modules = build_modules(
    [I280Queue],
    notifiers,
    log)

# Debugging

debug_level = logging.DEBUG if args.d else logging.INFO

LogHelper.initialize_console_logging(log, debug_level)

log.info('Starting')
app = LogfileProcessor(modules, log)
app.from_file(args.logfile, args.instance, args.hostname)
app.log_stats()






#!python3
# 
import argparse
import csv
import re
import os
import sys
import logging
from datetime import datetime, timedelta

log = logging.getLogger('logger')

class LogHelper:

    @staticmethod
    def initialize_console_logging(log_level):

        ch = logging.StreamHandler(sys.stdout)
        
        ch.setLevel(log_level)
        log.setLevel(log_level)

        formatter = logging.Formatter(
            '%(asctime)s: %(levelname)s: %(message)s',
            '%Y-%m-%d %H:%M:%S')

        ch.setFormatter(formatter)
        log.addHandler(ch)


class ParserError(Exception):
    pass

class LogRecord:

    logformat_regex = r'(.{28}) (.+?) \[(.*?)\] (.*?) \[(.+?)\] (.+?): (.+)'

    def __init__(self, record):
        m = re.match(self.logformat_regex, record)
        if not m:
            raise ParserError('Invalid logfile format')
        self.record = record
        self.str_timestamp=m.group(1)
        self.timestamp = datetime.strptime(self.str_timestamp[0:23],'%Y-%m-%d %H:%M:%S.%f')
        # self.timestamp = m.group(1)
        self.who=m.group(2)
        self.request=m.group(3)
        self.prog=m.group(4)
        self.identifier=m.group(5)
        self.severity=m.group(6)
        self.detail=m.group(7)
    def __repr__(self):
        return "{} {} [{}] {} [{}] {}: {}".format(
            self.str_timestamp, self.who,self.request,self.prog,
             self.identifier, self.severity, self.detail)

class RecordResult:
    def __init__(self, record):

        try:
            parsed_record = LogRecord(record)
            self.record = parsed_record
            self.is_error = False
            self.message = None
        except ParserError as e:
            self.record = None
            self.is_error = True
            self.message = str(e)

class Notify:
    def send_warning(self, message):
        raise NotImplementedError
    def send_info(self, message):
        raise NotImplementedError
    def send_error(self, message):
        raise NotImplementedError
    def send_crit(self, message):
        raise NotImplementedError
    def send_audit(self, message, headers):
        raise NotImplementedError

class Notifiers:
    def __init__(self, notifier_stack=[]):
        self.notifiers=notifier_stack

    # Not type safe
    def add_notifier(self, notifier):
        self.notifiers.append(notifier)

    def send_warning(self, message):
        for notifier in self.notifiers:
            notifier.send_warning(message)
    def send_error(self, message):
        for notifier in self.notifiers:
            notifier.send_error(message)
    def send_info(self, message):
        for notifier in self.notifiers:
            notifier.send_info(message)
    def send_crit(self, message):
        for notifier in self.notifiers:
            notifier.send_crit(message)
    def send_audit(self, message, headers=None):
        for notifier in self.notifiers:
            notifier.send_audit(message, headers)

class CSVNotify(Notify):

    ROTATE_KEEP = 10

    def __init__(self):
        self.initialized_files = {}

    def initialize_module(self, module):
        csv_filename = '{}-audit.csv'.format(module)
        if os.path.exists(csv_filename):
            for number in range(self.ROTATE_KEEP - 1,0,-1):
                old_name=csv_filename + "." + str(number)
                if os.path.exists(old_name):
                    new_name = csv_filename + "." + str(number+1)
                    os.rename(old_name, new_name)
            old_name = csv_filename
            new_name = csv_filename + ".1"
            os.rename(old_name, new_name)
        file_obj = open(csv_filename, "w", newline='')
        self.initialized_files[module]=file_obj

    def send_warning(self, message):
        return
    def send_info(self, message):
        return
    def send_crit(self, message):
        return
    def send_error(self, message):
        return
    def send_audit(self, module, data, headers=None):
        if module not in self.initialized_files:
            self.initialize_module(module)

        file_obj = self.initialized_files[module]
        if not isinstance(data, dict):
            data = {
                'Timestamp': datetime.now(),
                'Message':  data
            }
            headers = ['Timestamp', 'Message']
        else:
            if not headers:
                headers=list(data.keys())
        writer = csv.DictWriter(file_obj, fieldnames=headers)
        fppos=file_obj.tell()
        if fppos == 0:
            writer.writeheader()
        writer.writerow(data)
       
       
    
class ConsoleNotify(Notify):
    def send_warning(self, message):
        print("WARNING: {}".format(message))
    def send_info(self, message):
        print("INFO: {}".format(message))
    def send_crit(self, message):
        print("CRITICAL: {}".format(message))
    def send_error(self, message):
        print("ERROR: {}".format(message))
    def send_audit(self, message, headers):
        return

class i280Transaction:
    def __init__(self, start_date):
        self.start = start_date
        self.end = None
        self.correlation_id = None

class hid_msgsvc_ucpath:

    def __init__(self, notifier):
        
        self.states  = {}
        self.transactions = {}
        self.description = 'i280 Queueside'
        self.identifier = 'i280queue'
        self.notifier = notifier

        self.clear_statistics()

    def clear_statistics(self):
        self.i280_total = 0
        self.i280_fail = 0
        self.i280_ok = 0
        self.start = None
        self.end = None
        self.queue_durations = []

    def log_statistics(self):

        log.info('{} total i280 mesasages detected'.format(self.i280_total))
        log.info('{} i280 messages succesfully queued'.format(self.i280_ok))
        log.info('{} i280 messages failed to queue'.format(self.i280_fail))

        if self.queue_durations:
            average_queue_duration = sum(self.queue_durations) / len(self.queue_durations)
            min_queue_duration = min(self.queue_durations)
            max_queue_duration = max(self.queue_durations)
            log.info('Average queue delay: {}'.format(str(timedelta(microseconds=average_queue_duration))))
            log.info('Minimium queue delay: {}'.format(str(timedelta(microseconds=min_queue_duration))))
            log.info('Maximum queue delay: {}'.format(str(timedelta(microseconds=max_queue_duration))))


    def _setstate(self, identifier, state):
        self.states[identifier] = state
        return state
    def _get_state(self, identifier):
        
        state = self.states.get(identifier)
        if state is None:
            return self._setstate(identifier, 0)
        return state        

    # Create and update transactions store

    def _start_transaction(self, identifier, start_date):
        if self.transactions.get(identifier):
            del self.transactions[identifier]
        self.transactions[identifier] = i280Transaction(start_date)
    def _add_correlation_id(self,identifier, correlation_id):
        obj = self.transactions.get(identifier)
        if obj:
            obj.correlation_id = correlation_id
        else:
            raise ValueError("No transaction!")
    def _finish_transaction(self, identifier, end_date):
        obj = self.transactions.get(identifier)
        if obj:
            obj.end = end_date
        else:
            raise ValueError("No transaction!")
 
    # Main entry point

    def process_record(self, record):
        if record.prog[0:22] != 'hid_msgsvc:UCPATH.i280':
            return None

        if self.start is None or record.timestamp < self.start:
            self.start = record.timestamp

        if self.end is None or record.timestamp > self.end:
            self.end = record.timestamp

        state = self._get_state(record.identifier)
        if state == 0:
            if record.detail in ('Message failed to process via worker', 'Message sent to worker'):
                self.notifier.send_error('Premature end of transaction')
            elif record.detail == 'Begin Transaction':
                self._setstate(record.identifier,1)
                self._start_transaction(record.identifier, record.timestamp)
                self.i280_total += 1
        elif state == 1:
            if record.detail in ('Message failed to process via worker', 'Message sent to worker'):
                self.notifier.send_error('{}: Premature end of transaction'.format(record.str_timestamp))
                self._setstate(record.identifier, 0)
            if record.detail.startswith('Correlation ID: '):
                corr_id = record.detail[16:]
                log.debug('Correlation ID: {}'.format(corr_id))
                obj = self.transactions.get(record.identifier)
                if obj:
                    if obj.correlation_id:
                        self.notifier.send_warning('A new correlation ID [{}] at timestamp {} is not expected. The last one [{}] at timestamp {} did not finish'.format(
                            corr_id, record.str_timestamp, obj.correlation_id, obj.start_date))
                        self._setstate(self.identifier, 0)
                    else:
                        self._add_correlation_id(record.identifier, corr_id)
                self._setstate(record.identifier, 2)
        elif state == 2:
            obj = self.transactions.get(record.identifier)
            if not obj:
                self.notifier.send_error('State mismatch looking for end transaction')
                self._setstate(record.identifier, 0)
                return True
            if obj and not obj.correlation_id:
                self.notifier.send_error('State mismatch. No correlation ID')
                self._setstate(record.identifier, 0)
                return True

            if record.detail == 'Message failed to process via worker':
                self._finish_transaction(record.identifier, record.timestamp)
                duration_ms = (obj.end - obj.start).microseconds
                duration_s = (obj.end - obj.start).seconds
                self.notifier.send_crit('i280 [{}] failed to submit to worker. Time in queue: {} seconds'.format(obj.correlation_id, duration_s))
                self._setstate(record.identifier, 0)
                self.i280_fail += 1
                self.queue_durations.append(duration_ms)
                csvdata = {
                    'Receive Timestamp': obj.start.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                    'OK': 0,
                    'Correlation ID:': obj.correlation_id
                } 
                self.notifier.send_audit(self.identifier, csvdata)
                return True

            if record.detail == 'Message sent to worker':
                self._finish_transaction(record.identifier, record.timestamp)
                duration_ms = (obj.end - obj.start).microseconds
                duration_s = (obj.end - obj.start).seconds
                self.notifier.send_info('i280 [{}] submitted succesfully to worker. Time in queue: {} seconds'.format(obj.correlation_id, duration_s))
                self._setstate(record.identifier, 0)
                self.i280_ok += 1
                self.queue_durations.append(duration_ms)
                csvdata = {
                    'Receive Timestamp': obj.start.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                    'OK': 1,
                    'Correlation ID:': obj.correlation_id
                } 
                self.notifier.send_audit(self.identifier, csvdata)
                return True            
        return True


class LogfileProcessor:
    def __init__(self, notifiers):

        self.start = None
        self.end = None
 
        self.modules = {}
        for module in [hid_msgsvc_ucpath]:
            obj = module(notifiers)
            self.modules[obj.identifier] = obj

    def logfile_reader(self, file_object):

        record=''
        eof = False
        while not eof:
            line = file_object.readline()
            if line == '':
                data = record
                eof = True
                if data:
                    yield(RecordResult(data))

            line = line.rstrip()
            if line and line[0] == '\x18':
                data = record
                record = line[1:]
                if data:
                    yield(RecordResult(data))
            else:
                record +=  '{}\n'.format(line)    

    def from_file(self, filename):
        with open(filename) as logfile:
            for result in self.logfile_reader(logfile):
                if result.is_error:
                    log.error('Error reading entry: {}'.format(result.message))
                else:
                    if self.start is None or result.record.timestamp < self.start:
                        self.start = result.record.timestamp

                    if self.end is None or result.record.timestamp > self.end:
                        self.end = result.record.timestamp

                    for module in list(self.modules.values()):
                        module.process_record(result.record)

    def log_stats(self):
        for module in list(self.modules.values()):
            log.info('Statistics for module {}'.format(module.description))
            module.log_statistics()
        log.info('Statistics ** Logfile wide **')

        if self.start:
            start_str=str(self.start)
        else:
            start_str = 'Undefined'

        if self.end:
            end_str =str(self.end)
        else:
            end_Str = 'Undefined'

        log.info('First entry: {}'.format(start_str))
        log.info('Last entry: {}'.format(end_str))
        if self.start and self.end:
            log.info('Duration: {}'.format(self.end - self.start))



parser = argparse.ArgumentParser('Log Analyzer')
parser.add_argument('--d', help='Debug mode', action='store_true')
parser.add_argument('--csv', action='store_true', help='Write audit data for each module to csv files')
parser.add_argument('logfile', help='Log file to parse')
args = parser.parse_args()

notifiers = Notifiers()
notifiers.add_notifier(ConsoleNotify())
if args.csv:
    notifiers.add_notifier(CSVNotify())
if args.d:
    debug_level = logging.DEBUG
else:
    debug_level = logging.INFO



LogHelper.initialize_console_logging(debug_level)

log.info('Starting')
app = LogfileProcessor(notifiers)
app.from_file(args.logfile)
app.log_stats()






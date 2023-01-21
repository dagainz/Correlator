from datetime import datetime, timedelta
from common.util import Module
from common.event import NoticeEvent, ErrorEvent, EventProcessor

# from notify import Notifiers, Notification

"""This module reports on i280 activity through the Message Queue"""


class I280Transaction:
    def __init__(self, start_date):
        self.start = start_date
        self.end = None
        self.correlation_id = None


class I280Queue(Module):

    def __init__(self, processor: EventProcessor, log):

        self.log = log
        self.processor = processor
        self.description = 'I280 Queue'
        self.identifier = 'I280Queue'
        self.module_name = self.identifier

        self.states = {}
        self.transactions = {}
        self.i280_total = 0
        self.i280_fail = 0
        self.i280_ok = 0
        self.start = None
        self.end = None
        self.queue_durations = []
        self.log = log

    def clear_statistics(self):
        self.i280_total = 0
        self.i280_fail = 0
        self.i280_ok = 0
        self.start = None
        self.end = None
        self.queue_durations = []

    def statistics(self):

        messages = [
            '{} total i280 messages detected'.format(self.i280_total),
            '{} i280 messages successfully queued'.format(self.i280_ok),
            '{} i280 messages failed to queue'.format(self.i280_fail)
        ]

        if self.queue_durations:
            average_queue_duration = sum(self.queue_durations) / len(
                self.queue_durations)
            min_queue_duration = min(self.queue_durations)
            max_queue_duration = max(self.queue_durations)
            messages.extend([
                'Average queue delay: {}'.format(str(timedelta(
                    microseconds=average_queue_duration))),
                'Minimium queue delay: {}'.format(str(
                    timedelta(microseconds=min_queue_duration))),
                'Maximum queue delay: {}'.format(str(
                    timedelta(microseconds=max_queue_duration)))
            ])

        return messages

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
        """Initialize an I280 transaction"""
        if self.transactions.get(identifier):
            del self.transactions[identifier]
        self.transactions[identifier] = I280Transaction(start_date)

    def _add_correlation_id(self, identifier, correlation_id):
        """Adds a correlation ID to an initialized transaction"""

        obj = self.transactions.get(identifier)
        if obj:
            obj.correlation_id = correlation_id
        else:
            raise ValueError("No transaction!")

    def _finish_transaction(self, identifier, end_date):
        """finishes the transaction."""
        obj = self.transactions.get(identifier)
        if obj:
            obj.end = end_date
        else:
            raise ValueError("No transaction!")

    # Main entry point

    def process_record(self, record):

        # Handle both cases of workers from inside the message service
        # and from the command line I280 processor.

        if (
                not record.prog.startswith('hid_msgsvc:UCPATH.i280') and
                not record.prog.startswith('soap_server:UCPATH.i280')):
            return None

        if self.start is None or record.timestamp < self.start:
            self.start = record.timestamp

        if self.end is None or record.timestamp > self.end:
            self.end = record.timestamp

        state = self._get_state(record.identifier)
        if state == 0:
            if record.detail in [
                    'Message failed to process via worker',
                    'Message sent to worker']:
                self.dispatch_event(ErrorEvent(
                    'Premature end of transaction',
                    record=record))
            elif record.detail == 'Begin Transaction':
                self._setstate(record.identifier, 1)
                self._start_transaction(record.identifier, record.timestamp)
                self.i280_total += 1
        elif state == 1:
            if record.detail in [
                'Message failed to process via worker',
                    'Message sent to worker']:

                self.dispatch_event(ErrorEvent(
                    'Premature end of transaction',
                    record=record))

                self._setstate(record.identifier, 0)
            if record.detail.startswith('Correlation ID: '):
                corr_id = record.detail[16:]
                self.log.debug('Correlation ID: {}'.format(corr_id))
                obj = self.transactions.get(record.identifier)
                if obj:
                    if obj.correlation_id:
                        self.dispatch_event(ErrorEvent(
                            'Correlation ID at this time is not expected',
                            record=record))
                        self._setstate(self.identifier, 0)
                    else:
                        self._add_correlation_id(record.identifier, corr_id)
                self._setstate(record.identifier, 2)
        elif state == 2:
            obj = self.transactions.get(record.identifier)
            if not obj:
                self.dispatch_event(ErrorEvent(
                    'State mismatch looking for end transaction',
                    record=record))
                self._setstate(record.identifier, 0)
                return True
            if obj and not obj.correlation_id:
                self.dispatch_event(ErrorEvent(
                    'State mismatch. No correlation ID',
                    record=record))
                self._setstate(record.identifier, 0)
                return True

            if record.detail == 'Message failed to process via worker':
                self._finish_transaction(record.identifier, record.timestamp)
                duration_ms = (obj.end - obj.start).microseconds
                duration_s = (obj.end - obj.start).seconds
                self.dispatch_event(ErrorEvent(
                    'i280 [{}] failed to submit to worker. Time in queue: '
                    '{} seconds'.format(obj.correlation_id, duration_s),
                    record=record))

                self._setstate(record.identifier, 0)
                self.i280_fail += 1
                self.queue_durations.append(duration_ms)
                csvdata = {
                    'Receive Timestamp': obj.start.strftime(
                        '%Y-%m-%d %H:%M:%S.%f')[:-3],
                    'OK': 0,
                    'Correlation ID:': obj.correlation_id
                }
                # self.notifier.send_audit(self.identifier, csvdata)
                return True

            if record.detail == 'Message sent to worker':
                self._finish_transaction(record.identifier, record.timestamp)
                duration_ms = (obj.end - obj.start).microseconds
                duration_s = (obj.end - obj.start).seconds
                self.dispatch_event(NoticeEvent(
                    'i280 [{}] submitted successfully to worker. Time in '
                    'queue: {} seconds'.format(obj.correlation_id, duration_s),
                    record=record))

                self._setstate(record.identifier, 0)
                self.i280_ok += 1
                self.queue_durations.append(duration_ms)
                csvdata = {
                    'Receive Timestamp': obj.start.strftime(
                        '%Y-%m-%d %H:%M:%S.%f')[:-3],
                    'OK': 1,
                    'Correlation ID:': obj.correlation_id
                }
                # self.notifier.send_audit(self.identifier, csvdata)
                return True
        return True



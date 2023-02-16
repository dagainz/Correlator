"""
Correlator module for:

   The Bravura Security Inc Identity Management product suite

Process: Discovery

"""
import logging
from mako.template import Template

from Correlator.event import EventProcessor, AuditEvent
from Correlator.util import Module
from Correlator.bravura import IDMSyslogRecord

log = logging.getLogger(__name__)


class DiscoveryStatsEvent(AuditEvent):

    audit_id = 'module-stats'
    fields = [
        'num_discoveries'
    ]

    def __init__(self, data):
        super().__init__(self.audit_id, data)

        self.template_txt = Template(
            '${num_discoveries} total discoveries.')


class Discovery(Module):

    def __init__(self, processor: EventProcessor):

        self.processor = processor
        self.description = 'Discovery'
        self.identifier = 'Discovery'
        self.module_name = self.identifier

        self.states = {}

        self.discoveries = 0

    def clear_statistics(self):
        self.discoveries = 0

    def statistics(self, reset=False):

        data = {
            'num_discoveries': self.discoveries
        }
        self.dispatch_event(DiscoveryStatsEvent(data))

        if reset:
            self.clear_statistics()

    def _setstate(self, identifier, state):
        self.states[identifier] = state
        return state

    def _get_state(self, identifier):

        state = self.states.get(identifier)
        if state is None:
            return self._setstate(identifier, 0)
        return state

        # Create and update transactions store

    @staticmethod
    def tostring(record):
        return (f'{record.timestamp} {record.hostname} {record.instance} '
                f'{record.prog} {record.identifier} {record.msgid} '
                f'{record.detail}')

    def process_iddiscover(self, record):
        print(f'IDDISCOVER: {self.tostring(record)}')

    def process_psupdate(self, record):
        print(f'PSUPDATE: {self.tostring(record)}')

    def process_iddb(self, record):
        print(f'IDDB: {self.tostring(record)}')

    def process_record(self, syslog_record):

        record = IDMSyslogRecord(syslog_record.original_record)

        if record.prog.startswith('psupdate.exe'):
            self.process_psupdate(record)
        elif record.prog.startswith('iddiscover.exe'):
            self.process_iddiscover(record)
        elif record.prog.startswith('iddb.exe'):
            self.process_iddb(record)

        return True



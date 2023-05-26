"""
Correlator module for: Centos 8 Linux sshd

Process: logins

"""

import logging
import re
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from Correlator.Event.core import AuditEvent
from Correlator.util import (
    Module, CountOverTime, format_timestamp)
from Correlator.config import GlobalConfig, ConfigType

log = logging.getLogger(__name__)

SSHDConfig = [
    {
        'module.sshd.login_failure_window': {
            'default': 300,
            'desc': 'Amount of time in seconds to remember the login failures,'
                    'per host',
            'type': ConfigType.INTEGER
        }
    },
    {
        'module.sshd.login_failure_limit': {
            'default': 5,
            'desc': 'Number of login failures per host per module.sshd.login_'
                    'failure_window seconds',
            'type': ConfigType.INTEGER
        }
    },
    {
        'module.sshd.max_transaction_age': {
            'default': 2880,
            'desc': 'How many minutes after creation a transaction is valid',
            'type': ConfigType.INTEGER
        }
    }

]


class SSHDLoginEvent(AuditEvent):

    audit_id = 'sshd.login'
    fields = ['timestamp', 'auth', 'user', 'addr', 'port', 'key', 'failures',
              'start', 'finish', 'duration']

    def __init__(self, data):

        table = [
                ['Login ID:', '${user}'],
                ['Remote host:', '${addr}:${port}'],
                ['Key fingerprint:', '${key}'],
                ['Auth type:', '${auth}'],
                ['Number of failures:', '${failures}'],
                ['Session start:', '${start}'],
                ['Session end:', '${finish}'],
                ['Session duration:', '${duration}'],
            ]

        super().__init__(self.audit_id, data, table_data=table)
        self.audit_desc = ('A user ssh login session was established and '
                           'terminated normally')


class SSHDLoginFailedEvent(AuditEvent):

    audit_id = 'sshd.login-failed'
    fields = ['timestamp', 'user', 'addr', 'port', 'failures']

    def __init__(self, data):
        table_data = [
            ['Attempted login ID:', '${user}'],
            ['Remote host:', '${addr}:${port}'],
            ['Number of failures:', '${failures}'],
        ]
        super().__init__(self.audit_id, data, table_data=table_data)

        self.is_error = True
        self.audit_desc = ('A login attempt was rejected because of too many '
                           'attempts with an incorrect password')


class SSHDLoginsExceededEvent(AuditEvent):

    audit_id = 'sshd.login-retry'
    fields = ['timestamp', 'host']

    def __init__(self, data):
        table_data = [
            ['Remote Host:', '${host}']
        ]
        super().__init__(self.audit_id, data, table_data=table_data)
        self.audit_desc = (
            'A remote host has exceeded the allowed number of login attempts')


class SSHDStatsEvent(AuditEvent):

    audit_id = 'module-stats'
    fields = [
        'login_sessions',
        'denied',
        'lockouts',
        'expired',
        'partial'
    ]

    def __init__(self, data):

        table_data = [
            ['Login sessions:', '${login_sessions}'],
            ['Denied logins:', '${denied}'],
            ['Host lockouts:', '${lockouts}'],
            ['Expired transactions', '${expired}'],
            ['Partial transactions', '${partial}'],
        ]

        super().__init__(self.audit_id, data, table_data=table_data)

        self.audit_desc = 'Statistics for the SSH Logins module'


@dataclass
class SSHDStore:

    host_store: dict = field(default_factory=lambda: {})
    states: dict = field(default_factory=lambda: {})
    transactions: dict = field(default_factory=lambda: {})
    login_sessions: int = 0
    denied: int = 0
    lockouts: int = 0
    expired: int = 0


class SSHD(Module):

    GlobalConfig.add(SSHDConfig)

    def __init__(self):

        super().__init__()

        self.description = 'OpenSSH Server SSH Logins'
        self.identifier = 'sshd_logins'
        self.module_name = self.identifier

        self.model = SSHDStore

        self.expiry_seconds = GlobalConfig.get(
            'module.sshd.login_failure_window')
        self.failure_limit = GlobalConfig.get(
            'module.sshd.login_failure_limit')
        self.max_transaction_age = GlobalConfig.get(
            'module.sshd.max_transaction_age')

        self.address_store = None

    def maintenance(self):
        """ perform module maintenance

        Gaps in logs can result in transactions sticking around forever.
        This code removes old transactions from the store.

        """

        total_transactions = 0
        expired_transactions = 0

        now = datetime.now()

        for transaction in list(self.store.transactions.keys()):
            total_transactions += 1
            expires_on = (self.store.transactions[transaction]['timestamp'] +
                          timedelta(minutes=self.max_transaction_age))

            if now > expires_on:
                expired_transactions += 1
                self.store.expired += 1
                self._clear_state(transaction)
                log.debug(f'Expired transaction {transaction}')

        if expired_transactions > 0:
            log.info(f'Expired {expired_transactions} transactions out of '
                     f'{total_transactions}.')
            # todo: Evaluate sending an event with details of all expired
            #  transactions.

    def timer_handler_hour(self, now):
        log.debug(f'Running scheduled maintenance '
                  f'(Now={format_timestamp(now)})')
        self.maintenance()

    def timer_handler_0_0(self, now):
        log.info(f'Running nightly maintenance '
                 f'(Now={format_timestamp(now)})')
        self.statistics(reset=True)

    def post_init_store(self):
        log.debug(
            'post_init_store: Initializing host counter from persistence store')
        self.address_store = CountOverTime(
            self.expiry_seconds, self.store.host_store)

    def clear_statistics(self):
        self.store.login_sessions = 0
        self.store.denied = 0
        self.store.lockouts = 0
        self.store.expired = 0

    def statistics(self, reset=False):

        data = {
            'login_sessions': self.store.login_sessions,
            'denied': self.store.denied,
            'lockouts': self.store.lockouts,
            'expired': self.store.expired,
            'partial': len(self.store.transactions)

        }
        self.dispatch_event(SSHDStatsEvent(data))

        if reset:
            self.clear_statistics()

    def _has_state(self, identifier):
        if self.store.states.get(identifier) is not None:
            return True
        return False

    def _set_state(self, identifier, state):
        self.store.states[identifier] = state
        return state

    def _get_state(self, identifier):

        state = self.store.states.get(identifier)
        if state is None:
            return self._set_state(identifier, 0)
        return state

    def _clear_state(self, identifier):

        if self.store.states.get(identifier):
            del self.store.states[identifier]
        if self.store.transactions.get(identifier):
            del self.store.transactions[identifier]

    @staticmethod
    def tostring(record):
        return (f'{record.timestamp} {record.hostname} {record.instance} '
                f'{record.prog} {record.identifier} {record.msg_id} '
                f'{record.detail}')

    @staticmethod
    def detect_invalid_user(string):
        m = re.match(r'Invalid user (\S+) from (\S+) port (\d+)', string)
        if m:
            return {
                'user': m.group(1),
                'addr': m.group(2),
                'port': m.group(3),
            }
        return None

    @staticmethod
    def detect_passwordfailure(string):

        m = re.match(r'Failed password for (\S+) from (\S+) port (\S+)', string)
        if not m:
            m = re.match(r'Failed password for invalid user (\S+) from (\S+) '
                         r'port (\S+)', string)
        if m:
            return {
                'user': m.group(1),
                'addr': m.group(2),
                'port': m.group(3),
            }

        return None

    @staticmethod
    def detect_authfailure(string):
        m = re.match(r'.+authentication failure;\s+(.+)\s*', string)
        if m:
            prop_str = m.group(1)
            props = dict(x.split('=') for x in re.split(' +', prop_str))
            if len(props) > 0:
                return props

        return None

    @staticmethod
    def detect_accepted(string):

        m = re.match(r'Accepted publickey for (\S+) from (\S+) port (\S+) '
                     r'ssh2: RSA (\S+)', string)
        if m:
            return {
                'auth': 'rsa',
                'user': m.group(1),
                'addr': m.group(2),
                'port': m.group(3),
                'key': m.group(4)
            }

        m = re.match(r'Accepted password for (\S+) from (\S+) port (\S+)',
                     string)

        if m:
            return {
                'auth': 'password',
                'user': m.group(1),
                'addr': m.group(2),
                'port': m.group(3),
                'key': None
            }

        return None
    
    @staticmethod
    def detect_open(string):

        m = re.match(r'pam_unix\(sshd:session\): session opened for user (\S+) '
                     r'by (\S+)', string)

        if m:
            return {
                'user': m.group(1),
                'by': m.group(2)
            }
        
        return None

    @staticmethod
    def detect_close(string):

        if string.startswith('Connection closed'):
            return {}

        if string.startswith('pam_unix(sshd:session): session closed'):
            return {}

        return None

    def process_record(self, record):

        if record.appname.lower() != 'sshd':
            return

        identifier = f'{record.hostname}.{record.proc_id}'

        if not self._has_state(identifier):

            props = self.detect_accepted(record.detail)
            if props:
                self._set_state(identifier, 0)
                addr = props.get('addr')
                self.store.transactions[identifier] = {
                    'timestamp': datetime.now(),
                    'auth': props.get('auth'),
                    'user': props.get('user'),
                    'addr': addr,
                    'port': props.get('port'),
                    'key': props.get('key'),
                    'failures': 0
                }
                log.debug(f'Clearing any failed attempts for host {addr}')
                self.address_store.clear(addr)
                log.debug(f'Authentication succeeded for '
                          f'{props.get("user")}')
                return

            props = self.detect_authfailure(record.detail)
            if props is not None:
                self._set_state(identifier, 0)

                self.store.transactions[identifier] = {
                    'timestamp': datetime.now(),
                    'auth': None,
                    'user': props.get('user'),
                    'addr': props.get('rhost'),
                    'port': None,
                    'key': None,
                    'failures': 0
                }
                log.debug(f'Authentication failed for {props.get("user")}')
                return

            props = self.detect_invalid_user(record.detail)
            if props is not None:
                self._set_state(identifier, 0)
                self.store.transactions[identifier] = {
                    'timestamp': datetime.now(),
                    'auth': None,
                    'user': props.get('user'),
                    'addr': props.get('addr'),
                    'port': props.get('addr'),
                    'key': None,
                    'failures': 0
                }
                log.debug(f'Invalid user {props.get("user")}')
                return

            log.debug(f'Skipping State - record: {str(record)}')

            return True

        state = self._get_state(identifier)
        trans = self.store.transactions[identifier]

        if state == 0:
            props = self.detect_passwordfailure(record.detail)
            if props is not None:
                host = props.get('addr')
                trans['failures'] += 1
                failures = self.address_store.add(host, record.timestamp)
                log.debug(f"{failures} failures for host {host}")
                if failures >= self.failure_limit:
                    # Dispatch SSHDLoginsExceededEvent
                    data = {
                        'timestamp': format_timestamp(datetime.now()),
                        'host': props.get('addr')
                    }
                    self.dispatch_event(
                        SSHDLoginsExceededEvent(data))
                    self.store.lockouts += 1
                return
            props = self.detect_open(record.detail)
            if props is not None:
                trans['start'] = record.timestamp
                self._set_state(identifier, 1)
                return
            props = self.detect_accepted(record.detail)
            if props is not None:
                host = props['addr']
                for field_name in ['auth', 'user', 'addr', 'port', 'key']:
                    trans[field_name] = props[field_name]
                log.debug(f'Clearing any failed attempts for host {host}')
                self.address_store.clear(host)

            props = self.detect_close(record.detail)
            if props is not None:
                self.store.denied += 1
                # Dispatch SSHDLoginFailedEvent
                data = {
                    'timestamp': format_timestamp(datetime.now())
                }
                for key in ['user', 'addr', 'port', 'failures']:
                    data[key] = trans[key]
                self.dispatch_event(
                    SSHDLoginFailedEvent(data))
                return
            log.debug(f'Skipping State 0 record: {str(record)}')
        elif state == 1:
            props = self.detect_close(record.detail)
            if props is not None:
                trans['finish'] = record.timestamp
                self.store.login_sessions += 1
                # Dispatch SSHDLoginEvent
                data = {
                    'timestamp': format_timestamp(datetime.now())
                }
                for key in [
                    'auth', 'user', 'addr', 'port', 'key', 'failures',
                        'start', 'finish']:
                    data[key] = trans[key]

                data['duration'] = str(trans['finish'] - trans['start'])
                self.dispatch_event(
                    SSHDLoginEvent(data))

                del self.store.transactions[identifier]
                del self.store.states[identifier]
                return
            log.debug(f'Skipping State 1 record: {str(record)}')

"""
Correlator module for: Centos 8 Linux sshd

Process: logins

"""

import re
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from Correlator.Event.core import Event, EventSeverity
from Correlator.util import Module, CountOverTime, format_timestamp
from Correlator.config_store import ConfigType

SSHDConfig = [
    {
        'login_failure_window': {
            'default': 300,
            'desc': 'Amount of time in seconds to remember the login failures,'
                    'per host',
            'type': ConfigType.INTEGER
        }
    },
    {
        'login_failure_limit': {
            'default': 5,
            'desc': 'Number of login failures per host per login_'
                    'failure_window seconds',
            'type': ConfigType.INTEGER
        }
    },
    {
        'max_transaction_age': {
            'default': 2880,
            'desc': 'How many minutes after creation a transaction is valid',
            'type': ConfigType.INTEGER
        }
    }

]


class SSHDLoginSucceeded(Event):

    schema = [
        ['user', 'Login ID'],
        ['auth', 'Authentication method'],
        ['addr', 'Remote host'],
        ['port', 'Remote port'],
        ['failures', 'Failures prior'],
        ['start', 'Session start'],
        ['finish', 'Session end'],
        ['duration', 'Session Duration'],
        ['key', 'Public key fingerprint'],

    ]

    templates = {
        'text/plain': {
            'summary': 'User ${user} from host ${addr}:${port} succesfully authenticated using ${auth} authentication after ${failures} failed attempt(s) with a session duration of ${duration}'
        },
        'text/html': {
            'summary': 'User <strong>${user}</strong> from host <strong>${addr}:${port}</strong> succesfully authenticated using <strong>${auth}</strong> authentication after <strong>${failures}</strong> failed attempt(s) with a session duration of <strong>${duration}</strong>'
        }
    }


class SSHDLoginFailed(Event):

    schema = [
        ['user', 'Attempted login ID'],
        ['addr', 'Remote host'],
        ['port', 'Remote port'],
        ['failures', 'Number of failures']
    ]
    templates = {
        'text/plain': {
            'summary': 'User ${user} from host ${addr}:${port} failed to login after ${failures} failures'
        },
        'text/html': {
            'summary': 'User <strong>${user}</strong> from host <strong>${addr}:${port}</strong> failed to login after <strong>${failures}</strong> failures'
        }
    }
    severity_override = EventSeverity.Error


class SSHDAttemptsExceeded(Event):

    schema = [
        ['host', 'Remote host']
    ]

    templates = {
        'text/plain': {
            'summary': 'User ${user} from host ${addr}:${port} failed to login after ${failures} failures'
        }
    }

    # summary_template = 'The host at ${host} has exceeded the maximum number of failed login attempts within the configured time window'
    severity_override = EventSeverity.Error


class SSHDStats(Event):

    schema = [
        ['login_sessions', 'Login sessions'],
        ['denied', 'Denied logins'],
        ['lockouts', 'Host lockouts'],
        ['expired', 'Expired transactions'],
        ['partial', 'Partial transactions'],
    ]
    summary_template = 'Statistics: ${login_sessions} logion session(s), ${denied} denied login(s),  ${lockouts} host lockout(s), ${expired} expired transaction(s), ${partial} partial transaction(s)'


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

    # GlobalConfig.add(SSHDConfig)

    def __init__(self, module_name: str):

        super().__init__(module_name)

        self.description = 'OpenSSH Server SSH Logins'
        self.identifier = 'sshd_logins'
        self.model = SSHDStore
        self.address_store = None

        self.add_config(SSHDConfig)

        self.expiry_seconds = None
        self.failure_limit = None
        self.max_transaction_age = None

    def initialize(self):

        self.log.debug('Process module related configuration items')

        self.expiry_seconds = self.get_config('login_failure_window')
        self.failure_limit = self.get_config('login_failure_limit')
        self.max_transaction_age = self.get_config('max_transaction_age')

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
                self.log.debug(f'Expired transaction {transaction}')

        if expired_transactions > 0:
            self.log.info(f'Expired {expired_transactions} transactions out'
                          f' of {total_transactions}.')

            # todo: Evaluate sending an event with details of all expired
            #  transactions.

    def timer_handler_hour(self, now):
        self.log.debug(f'Running scheduled maintenance (Now='
                       f'{format_timestamp(now)})')
        self.maintenance()

    def timer_handler_0_0(self, now):
        self.log.info(f'Running nightly maintenance '
                      f'(Now={format_timestamp(now)})')
        self.statistics(reset=True)

    def post_init_store(self):
        self.log.debug(
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
        self.dispatch_event(SSHDStats(data))

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

    # @staticmethod
    def detect_authfailure(self, string):
        m = re.match(r'.+authentication failure;\s+(.+)\s*', string)
        if m:
            prop_str = m.group(1).strip()
            self.log.debug(f'detect_authfailure: prop_str={prop_str}')
            props = dict(x.split('=') for x in re.split(' +', prop_str))
            if len(props) > 0:
                return props

        return None

    @staticmethod
    def detect_accepted(string):

        # self.log.debug(f'detect_accepted: string=[{string}]')

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
                self.log.debug(f'Clearing any failed attempts for host {addr}')
                self.address_store.clear(addr)
                self.log.debug(f'Authentication succeeded for {props.get("user")}')
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
                self.log.debug(f'Authentication failed for {props.get("user")}')
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
                self.log.debug(f'Invalid user {props.get("user")}')
                return

            self.log.debug(f'Skipping State - record: {str(record)}')

            return True

        state = self._get_state(identifier)
        trans = self.store.transactions[identifier]

        if state == 0:
            props = self.detect_passwordfailure(record.detail)
            if props is not None:
                host = props.get('addr')
                trans['failures'] += 1
                failures = self.address_store.add(host, record.timestamp)
                self.log.debug(f"{failures} failures for host {host}")
                if failures >= self.failure_limit:
                    # Dispatch SSHDAttemptsExceeded
                    data = { 'host': props.get('addr')
                    }
                    self.dispatch_event(
                        SSHDAttemptsExceeded(data))
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
                self.log.debug(f'Clearing any failed attempts for host {host}')
                self.address_store.clear(host)

            props = self.detect_close(record.detail)
            if props is not None:
                self.store.denied += 1
                # Dispatch SSHDLoginFailed
                data =  {}
                for key in ['user', 'addr', 'port', 'failures']:
                    data[key] = trans[key]
                self.dispatch_event(
                    SSHDLoginFailed(data))
                return
            self.log.debug(f'Skipping State 0 record: {str(record)}')
        elif state == 1:
            props = self.detect_close(record.detail)
            if props is not None:
                trans['finish'] = record.timestamp
                self.store.login_sessions += 1
                # Dispatch SSHDLoginSucceeded
                data = {}
                for key in [
                    'auth', 'user', 'addr', 'port', 'key', 'failures',
                        'start', 'finish']:
                    data[key] = trans[key]

                data['duration'] = str(trans['finish'] - trans['start'])
                self.dispatch_event(
                    SSHDLoginSucceeded(data))

                del self.store.transactions[identifier]
                del self.store.states[identifier]
                return
            self.log.debug(f'Skipping State 1 record: {str(record)}')

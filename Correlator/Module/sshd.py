"""
Correlator module for: Centos 8 Linux sshd

Process: logins

"""

import logging
import re
from datetime import datetime
from dataclasses import dataclass
from mako.template import Template

from Correlator.event import EventProcessor, AuditEvent
from Correlator.util import (
    Module, CountOverTime, GlobalConfig, format_timestamp)

log = logging.getLogger(__name__)

DEFAULT_FAILURE_WINDOW = 300     # 5 minutes
FAILURE_WINDOW_PARAM = 'module.sshd.login_failure_window'

DEFAULT_FAILURE_LIMIT = 5
FAILURE_LIMIT_PARAM = 'module.sshd.login_failure_limit'


class SSHDLoginEvent(AuditEvent):

    audit_id = 'sshd_login'
    fields = ['timestamp', 'auth', 'user', 'addr', 'port', 'key', 'failures',
              'start', 'finish', 'duration']

    def __init__(self, data):
        super().__init__(self.audit_id, data)


class SSHDLoginFailedEvent(AuditEvent):

    audit_id = 'sshd_login_failed'
    fields = ['timestamp', 'user', 'addr', 'port', 'failures']

    def __init__(self, data):
        super().__init__(self.audit_id, data)


class SSHDLoginsExceededEvent(AuditEvent):

    audit_id = 'sshd_login_retry'
    fields = ['timestamp', 'host']

    def __init__(self, data):
        super().__init__(self.audit_id, data)


class SSHDStatsEvent(AuditEvent):

    audit_id = 'module-stats'
    fields = [
        'login_sessions',
        'denied',
        'lockouts'
    ]

    def __init__(self, data):
        super().__init__(self.audit_id, data)

        self.template_txt = Template(
            '${login_sessions} total successful logins, ${denied} unsuccessful'
            ' logins, ${lockouts} lockouts.')


@dataclass
class SSHDState:

    host_store: dict
    states: dict
    transactions: dict
    login_sessions: int = 0
    denied: int = 0
    lockouts: int = 0

    def __init__(self):
        self.states = {}
        self.transactions = {}
        self.host_store = {}


class SSHD(Module):

    def __init__(self):

        super().__init__()

        self.description = 'OpenSSH Server SSH Logins'
        self.identifier = 'sshd_logins'
        self.module_name = self.identifier

        self.expiry_seconds = GlobalConfig.get(
            FAILURE_WINDOW_PARAM, DEFAULT_FAILURE_WINDOW)
        self.failure_limit = GlobalConfig.get(
            FAILURE_LIMIT_PARAM, DEFAULT_FAILURE_LIMIT)

        self.address_store = None

        # CountOverTime(self.expiry_seconds)

    def init_state(self, state: dict):

        if 'data' not in state:
            state['data'] = SSHDState()
            log.debug('Initialized new state')
        else:
            log.debug('Initialized previous state')

        self.state = state['data']

        self.address_store = CountOverTime(
            self.expiry_seconds, self.state.host_store)

    def clear_statistics(self):
        self.state.login_sessions = 0
        self.state.denied = 0
        self.state.lockouts = 0

    def statistics(self, reset=False):

        data = {
            'login_sessions': self.state.login_sessions,
            'denied': self.state.denied,
            'lockouts': self.state.lockouts,

        }
        self.dispatch_event(SSHDStatsEvent(data))

        if reset:
            self.clear_statistics()

    def _has_state(self, identifier):
        if self.state.states.get(identifier) is not None:
            return True
        return False

    def _set_state(self, identifier, state):
        self.state.states[identifier] = state
        return state

    def _get_state(self, identifier):

        state = self.state.states.get(identifier)
        if state is None:
            return self._set_state(identifier, 0)
        return state

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

        if self.state is None:
            raise ValueError("Hey! State is None")

        if record is None:
            log.debug("Received heartbeat. No maintenance for this module")
            return

        if record.appname.lower() != 'sshd':
            return

        identifier = f'{record.hostname}.{record.proc_id}'

        if not self._has_state(identifier):

            props = self.detect_accepted(record.detail)
            if props:
                self._set_state(identifier, 0)
                addr = props.get('addr')
                self.state.transactions[identifier] = {
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

                self.state.transactions[identifier] = {
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
                self.state.transactions[identifier] = {
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
        trans = self.state.transactions[identifier]

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
                    self.state.lockouts += 1
                return
            props = self.detect_open(record.detail)
            if props is not None:
                trans['start'] = record.timestamp
                self._set_state(identifier, 1)
                return
            props = self.detect_accepted(record.detail)
            if props is not None:
                host = props['addr']
                for field in ['auth', 'user', 'addr', 'port', 'key']:
                    trans[field] = props[field]
                log.debug(f'Clearing any failed attempts for host {host}')
                self.address_store.clear(host)

            props = self.detect_close(record.detail)
            if props is not None:
                self.state.denied += 1
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
                self.state.login_sessions += 1
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

                del self.state.transactions[identifier]
                del self.state.states[identifier]
                return
            log.debug(f'Skipping State 1 record: {str(record)}')

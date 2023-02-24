"""
Correlator module for: Linux sshd

Process: logins

This module handles the following situations:

Standard password login / logout with no failure attempts

Accepted password for testguy from 192.168.1.85 port 50759 ssh2
pam_unix(sshd:session): session opened for user testguy by (uid=0)
Received disconnect from 192.168.1.85 port 50759:11: disconnected by us
Disconnected from user testguy 192.168.1.85 port 50759
pam_unix(sshd:session): session closed for user testguy

Standard password login / logout with one failure attempt

pam_unix(sshd:auth): authentication failure; logname= uid=0 euid=0 tty=ssh ruser= rhost=192.168.1.85  user=testguy
Failed password for testguy from 192.168.1.85 port 50809 ssh2
Accepted password for testguy from 192.168.1.85 port 50809 ssh2
pam_unix(sshd:session): session opened for user testguy by (uid=0)
Received disconnect from 192.168.1.85 port 50809:11: disconnected by user
Disconnected from user testguy 192.168.1.85 port 50809
pam_unix(sshd:session): session closed for user testguy

Failed login attempt

pam_unix(sshd:auth): authentication failure; logname= uid=0 euid=0 tty=ssh ruser= rhost=192.168.1.85  user=testguy
Failed password for testguy from 192.168.1.85 port 50930 ssh2
Failed password for testguy from 192.168.1.85 port 50930 ssh2
Failed password for testguy from 192.168.1.85 port 50930 ssh2
Connection closed by authenticating user testguy 192.168.1.85 port 50930 [preauth]
PAM 2 more authentication failures; logname= uid=0 euid=0 tty=ssh ruser= rhost=192.168.1.85  user=testguy

Attempt with invalid user ID

Invalid user baduser from 192.168.1.85 port 53090
pam_unix(sshd:auth): check pass; user unknown
pam_unix(sshd:auth): authentication failure; logname= uid=0 euid=0 tty=ssh ruser=
Failed password for invalid user baduser from 192.168.1.85 port 53090 ssh2
pam_unix(sshd:auth): check pass; user unknown
Failed password for invalid user baduser from 192.168.1.85 port 53090 ssh2
pam_unix(sshd:auth): check pass; user unknown
Failed password for invalid user baduser from 192.168.1.85 port 53090 ssh2
Connection closed by invalid user baduser 192.168.1.85 port 53090 [preauth]
PAM 2 more authentication failures; logname= uid=0 euid=0 tty=ssh ruser= rhost=192.1

"""

import logging
import re
from datetime import datetime
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


class SSHD(Module):

    def __init__(self, processor: EventProcessor):

        self.processor = processor
        self.description = 'OpenSSH Server SSH Logins'
        self.identifier = 'sshd_logins'
        self.module_name = self.identifier

        self.states = {}
        self.transactions = {}

        self.expiry_seconds = GlobalConfig.get(
            FAILURE_WINDOW_PARAM, DEFAULT_FAILURE_WINDOW)
        self.failure_limit = GlobalConfig.get(
            FAILURE_LIMIT_PARAM, DEFAULT_FAILURE_LIMIT)

        self.address_store = CountOverTime(self.expiry_seconds)

        self.login_sessions = 0
        self.denied = 0
        self.lockouts = 0

    def clear_statistics(self):
        self.login_sessions = 0
        self.denied = 0
        self.lockouts = 0

    def statistics(self, reset=False):

        data = {
            'login_sessions': self.login_sessions,
            'denied': self.denied,
            'lockouts': self.lockouts,

        }
        self.dispatch_event(SSHDStatsEvent(data))

        if reset:
            self.clear_statistics()

    def _has_state(self, identifier):
        if self.states.get(identifier) is not None:
            return True
        return False

    def _set_state(self, identifier, state):
        self.states[identifier] = state
        return state

    def _get_state(self, identifier):

        state = self.states.get(identifier)
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

        if record is None:
            log.debug("Keep alive")
            return

        if record.appname.lower() != 'sshd':
            return

        identifier = f'{record.hostname}.{record.proc_id}'

        if not self._has_state(identifier):

            props = self.detect_accepted(record.detail)
            if props:
                self._set_state(identifier, 0)
                addr = props.get('addr')
                self.transactions[identifier] = {
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

                self.transactions[identifier] = {
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
                self.transactions[identifier] = {
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
        trans = self.transactions[identifier]

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
                    self.lockouts += 1
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
                self.denied += 1
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
                self.login_sessions += 1
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

                del self.transactions[identifier]
                del self.states[identifier]
                return
            log.debug(f'Skipping State 1 record: {str(record)}')

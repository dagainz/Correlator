# Module: OpenSSH Login

## Overview

This module watches log records generated from OpenSSH to detect

- successful login sessions
- unsuccessful login attempts
- Potential hack attempts

It dispatches events in response with as much information about the transaction as it knows. Separate log entries
must be correlated together, with some information about the transaction coming from each.

*Note: Tested with OpenSSH 8.0p1 on Centos 8*

For the hack attempt detection, it counts the number of failed password attempts from a particular host over time. If
the count goes over a configurable threshold, an event is dispatched.

## Dispatched events

### SSHDLoginEvent (Audit Event)

This event is dispatched when a successful sshd login session *ends*

| Attribute | Value                                                                 |
|-----------|-----------------------------------------------------------------------|
| timestamp | timestamp of event                                                    |
| auth      | Authentication type (password, rsa)                                   |
| user      | Login ID                                                              |
| addr      | Remote Address                                                        |
| port      | Remote Port                                                           |
| key       | Key fingerprint (if applicable)                                       |
| failures  | Number of failed password attempts before successfully authenticating |
| start     | Timestamp of session start                                            |
| finish    | Timestamp of session end                                              |
| duration  | Session duration                                                      |



## Detection patterns

### Detecting a successful login

The module recognizes the following sequence as a straightforward successful login:

```
Accepted password for testguy from 192.168.1.85 port 50759 ssh2
pam_unix(sshd:session): session opened for user testguy by (uid=0)
Received disconnect from 192.168.1.85 port 50759:11: disconnected by us
Disconnected from user testguy 192.168.1.85 port 50759
pam_unix(sshd:session): session closed for user testguy
```

It recognizes the following sequence as a successful login with error retries. It counts the number of
failures to be collected:

```
pam_unix(sshd:auth): authentication failure; logname= uid=0 euid=0 tty=ssh ruser= rhost=192.168.1.85  user=testguy
Failed password for testguy from 192.168.1.85 port 50809 ssh2
Accepted password for testguy from 192.168.1.85 port 50809 ssh2
pam_unix(sshd:session): session opened for user testguy by (uid=0)
Received disconnect from 192.168.1.85 port 50809:11: disconnected by user
Disconnected from user testguy 192.168.1.85 port 50809
pam_unix(sshd:session): session closed for user testguy
```

### Detecting an unsuccessful login


```
pam_unix(sshd:auth): authentication failure; logname= uid=0 euid=0 tty=ssh ruser= rhost=192.168.1.85  user=testguy
Failed password for testguy from 192.168.1.85 port 50930 ssh2
Failed password for testguy from 192.168.1.85 port 50930 ssh2
Failed password for testguy from 192.168.1.85 port 50930 ssh2
Connection closed by authenticating user testguy 192.168.1.85 port 50930 [preauth]
PAM 2 more authentication failures; logname= uid=0 euid=0 tty=ssh ruser= rhost=192.168.1.85  user=testguy
```

### Detecting an attempt using an invalid ID:

```
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
```

## Testing 

### Run the module against the included capture file

    syslog_server --read-file data/sshd-1.cap --sshd

```
2023-02-27 13:41:19 syslog_server INFO: Reading from capture file data/sshd-1.cap
2023-02-27 13:41:19 event INFO: sshd_logins: Audit(sshd_login): Audit: timestamp=2023-02-27 13:41:19, auth=rsa, user=timp, addr=192.168.1.85, port=60116, key=SHA256:QaxveQJbYmX1Wmx/p2A7q+CJEZEySEl3Cnk79PVUY2A, failures=0, start=2023-02-20 15:12:47.771632, finish=2023-02-20 15:14:09.072459, duration=0:01:21.300827
2023-02-27 13:41:19 event INFO: sshd_logins: Audit(sshd_login): Audit: timestamp=2023-02-27 13:41:19, auth=password, user=testguy, addr=192.168.1.85, port=60138, key=None, failures=0, start=2023-02-20 15:14:35.667317, finish=2023-02-20 15:14:42.176438, duration=0:00:06.509121
2023-02-27 13:41:19 event INFO: sshd_logins: Audit(sshd_login_failed): Audit: timestamp=2023-02-27 13:41:19, user=testguy, addr=192.168.1.85, port=None, failures=3
2023-02-27 13:41:19 event INFO: sshd_logins: Audit(module-stats): 2 total successful logins, 1 unsuccessful logins, 0 lockouts.
2023-02-27 13:41:19 event INFO: syslog-server: Audit(system-stats): Sever session started at 2023-02-27 13:41:19 and ended at 2023-02-27 13:41:19 for a total duration of 0:00:00.001733
```

This illustrates 2 successful logins and one failed one. The successful ones comprised of one RSA auth and one password
auth.

### Run the module within a syslog server context.

*Note: A Linux system must be configured to forward log events to you*

    syslog_server --sshd

```
2023-02-27 13:51:24 syslog INFO: Server listening on 0.0.0.0:514
```

Log into the linux system, wait a few seconds, and then log off

```
2023-02-27 13:53:06 event INFO: sshd_logins: Audit(sshd_login): Audit: timestamp=2023-02-27 13:53:06, auth=password, user=testguy, addr=192.168.1.85, port=57631, key=None, failures=0, start=2023-02-27 13:53:00.430366, finish=2023-02-27 13:53:06.176757, duration=0:00:05.746391
```

Try to log in 5 times within 5 minutes, using an invalid password.

Login to the Linux system using a username that you know exists. After 3 failed password attempts, the server
will close the connection. An sshd_login_failed event will be dispatched. Establish a new SSH connection
to the Linux system and attempt to log in again using the same username. After 2 failed password_attempts, the
sshd_login_retry event will be dispatched.

```
2023-02-27 13:55:29 event INFO: sshd_logins: Audit(sshd_login_failed): Audit: timestamp=2023-02-27 13:55:29, user=testguy, addr=192.168.1.85, port=None, failures=3
2023-02-27 13:55:39 event INFO: sshd_logins: Audit(sshd_login_retry): Audit: timestamp=2023-02-27 13:55:39, host=192.168.1.85
```



# OpenSSH Login module

**Note**: This module is considered alpha quality at best. It for meant for educational purposes.

An OpenSSH login module is included with this distribution. It processes log events from an OpenSSH daemon 
to detect successful logins, unsuccessful logins, and potential hack attempts. It dispatches custom events in response.

For the hack detection, it counts the number of failed password attempts from a particular host over time. If the count
goes over a configurable threshold, an event is dispatched.

The syslog server combined with this module demonstrate a simple SIEM. It monitors and reports on ssh logins.
With an appropriate event handler, it could take a more effective action such as adding a firewall rule to bock the
remote host temporarily, or cut a ServiceNOW ticket via it's REST API to let the network team handle it.

This has been developed and tested using the OpenSSH server included with Centos 8.

### Run the server/module against a capture file

Dump the contents of the capture file

    caputil --in data/sshd-1.cap

```
2023-02-27 13:39:26 event INFO: Report: 2023-02-20 15:12:47: giganode1 sshd 2540460 Accepted publickey for timp from 192.168.1.85 port 60116 ssh2: RSA SHA256:QaxveQJbYm
2023-02-27 13:39:26 event INFO: Report: 2023-02-20 15:12:47: giganode1 sshd 2540460 pam_unix(sshd:session): session opened for user timp by (uid=0)
2023-02-27 13:39:26 event INFO: Report: 2023-02-20 15:14:09: giganode1 sshd 2540463 Received disconnect from 192.168.1.85 port 60116:11: disconnected by user
2023-02-27 13:39:26 event INFO: Report: 2023-02-20 15:14:09: giganode1 sshd 2540463 Disconnected from user timp 192.168.1.85 port 60116
2023-02-27 13:39:26 event INFO: Report: 2023-02-20 15:14:09: giganode1 sshd 2540460 pam_unix(sshd:session): session closed for user timp
2023-02-27 13:39:26 event INFO: Report: 2023-02-20 15:14:35: giganode1 sshd 2540647 Accepted password for testguy from 192.168.1.85 port 60138 ssh2
2023-02-27 13:39:26 event INFO: Report: 2023-02-20 15:14:35: giganode1 sshd 2540647 pam_unix(sshd:session): session opened for user testguy by (uid=0)
2023-02-27 13:39:26 event INFO: Report: 2023-02-20 15:14:42: giganode1 sshd 2540659 Received disconnect from 192.168.1.85 port 60138:11: disconnected by user
2023-02-27 13:39:26 event INFO: Report: 2023-02-20 15:14:42: giganode1 sshd 2540659 Disconnected from user testguy 192.168.1.85 port 60138
2023-02-27 13:39:26 event INFO: Report: 2023-02-20 15:14:42: giganode1 sshd 2540647 pam_unix(sshd:session): session closed for user testguy
2023-02-27 13:39:26 event INFO: Report: 2023-02-20 15:14:45: giganode1 sshd 2540712 pam_unix(sshd:auth): authentication failure; logname= uid=0 euid=0 tty=ssh ruser= 
2023-02-27 13:39:26 event INFO: Report: 2023-02-20 15:14:46: giganode1 sshd 2540712 Failed password for testguy from 192.168.1.85 port 60142 ssh2
2023-02-27 13:39:26 event INFO: Report: 2023-02-20 15:14:50: giganode1 sshd 2540712 Failed password for testguy from 192.168.1.85 port 60142 ssh2
2023-02-27 13:39:26 event INFO: Report: 2023-02-20 15:14:56: giganode1 sshd 2540712 Failed password for testguy from 192.168.1.85 port 60142 ssh2
2023-02-27 13:39:26 event INFO: Report: 2023-02-20 15:14:58: giganode1 sshd 2540712 Connection closed by authenticating user testguy 192.168.1.85 port 60142 [preauth]
2023-02-27 13:39:26 event INFO: Report: 2023-02-20 15:14:58: giganode1 sshd 2540712 PAM 2 more authentication failures; logname= uid=0 euid=0 tty=ssh ruser= rhost=192.1
```

Run the server against the capture file using the sshd module

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

### Run the server/module over the network

Configure the linux syslog daemon to forward log events to you. Run the syslog_server, enabling the sshd module:

    syslog_server --sshd

```
2023-02-27 13:51:24 syslog INFO: Server listening on 0.0.0.0:514
```

Log into the linux system, wait a few seconds, and then log off

```
2023-02-27 13:53:06 event INFO: sshd_logins: Audit(sshd_login): Audit: timestamp=2023-02-27 13:53:06, auth=password, user=testguy, addr=192.168.1.85, port=57631, key=None, failures=0, start=2023-02-27 13:53:00.430366, finish=2023-02-27 13:53:06.176757, duration=0:00:05.746391
```

Try to log in 5 times within 5 minutes, using an invalid password.

For this test I attempted to establish an ssh session from my mac to a linux VM using a username that I knew existed. 
After 3 failed password attempts, the server closed my connection and the sshd_login_failed event was dispatched. 
I then attempted to establish another session using the same username. After 2 failed password attempts the
sshd_login_retry event was dispatched.

```
2023-02-27 13:55:29 event INFO: sshd_logins: Audit(sshd_login_failed): Audit: timestamp=2023-02-27 13:55:29, user=testguy, addr=192.168.1.85, port=None, failures=3
2023-02-27 13:55:39 event INFO: sshd_logins: Audit(sshd_login_retry): Audit: timestamp=2023-02-27 13:55:39, host=192.168.1.85
```


## Detection patterns

The following patterns were observed when attempting the various use-cases.

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



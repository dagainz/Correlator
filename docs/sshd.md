# OpenSSH Login session module

An OpenSSH ssh server module is included with this distribution. It processes log events from an OpenSSH daemon 
to detect successful logins, unsuccessful logins, and potential hack attempts and dispatches custom events in response.

It detects potential hack attempts by counting the number of failed password attempts on a particular host over time
and comparing it to a configurable threshold.

This is an example of a simple SIEM. It would be more effective if it actually did something, like
add a firewall rule to bock the remote host, or cut a servicenow ticket and dispatch it to the network team 
for manual or automatic action.

This has been developed and tested using the OpenSSH server included with Centos 8.

## Detecting a successful login

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

## Detecting an unsuccessful login


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


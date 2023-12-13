# Features of this release 

This document describes the major functionality contained within this repository.

recap:

out-of-the-box functionality includes:

- RFC 5424 compliant TCP syslog server processes syslog records received from a remote system. It also has the
ability to capture received syslog packets to a file, and to use these capture files as input.
- An OpenSSH *logic module*: Detection logic that looks for patterns, such as **Successful login** in OpenSSH's
log stream, and dispatch *events* in response.
- Several *event handlers*: action logic that take action when these events occur.
  - Email: Generates an email from a template using mako, and send via SMTP.
  - CSV: Writes event data to rows in a csv file.
  - SMS: Sends a basic SMS via twilio.

And more!

# 
#### Front-ends

- RFC 5424 compliant TCP syslog server listens on the network and processes syslog data received from a remote system.
- Log file reader reads and processes log data contained in log files. This is implemented as a python class
that must be extended by subclassing it with code that contains logic to handle the format of your particular log file.

#### Logic modules

- The **sshd module** processes log records from an OpenSSH daemon and detects various scenarios.
- Integrated **report** module simply dispatches an event for every received log record. The event contains
a summary of the log record. This is the module that is activated when using the *report* app with the syslog server.

#### Event handlers

- **logback** - Simply dumps the event details to the python log (currently stdout). 
- **CSV** - Writes the event properties to fields in a CSV file.
- **e-mail** - Generate email messages using mako to render templates. Event properties are made available to mako to
use within the template.
- **sms** - Send a simple SMS containing the event details using twilio.

### Other stuff

- Disk file based persistence store to maintain system state between invocations (syslog server front-end)

#### Credential handling with python keyring

Event handlers often require the use of credentials with secrets. To avoid plain text passwords stored in configuration
files, Correlator delegates credential storage to python keyring. When correlator starts up, it queries all event
handlers that are active for the running application, for credentials that are required. If any of the credentials are
not found in the ring, Correlator will exit with a message indicating which ones are missing.

After adding the missing credentials to the ring by using a command line utility, Correlator can then start, and will
use those credentials for the event handlers.

## Requirements

- Python 3.10
- A Unix like system, or Docker.

## Limitations and known issues

Many, such as:

- Single thread. An event handler blocking forever will halt the system.
- Limited exception handling, making the system fragile.
- The syslog server services a single TCP connection.
- The event system has no retry or even audit capability. Its fire-and-forget.
- Config file currently is JSON format, which is less than ideal for a human but easy to use in code.



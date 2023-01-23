# Correlator

This software provides a log analysis system that consumes and processes log data, 
presumably generated from other systems or applications. 

## Architecture

### The Correlator Engine

The Correlator Engine is responsible for reading the log data and passing it through 
one or more Correlator Logic Modules for processing. During its execution, the Correlator
Engine may dispatch events to be handled independently by the Event Processor.
 
### The Event Processor

The Event Processor is responsible for processing and reacting to events dispatched 
by the Correlator Engine. The Event Processor forwards received events to one or more
Event Listeners for processing. 

### Correlator Logic Module 

The Correlator Logic Module implements logic that:
- Receives and interprets log data, maintaining state (The Correlation process).
- Detects situations and responds by creating and dispatching events that get handled 
by another, independent propcess.
- (Optionally) Maintain a running set of related statistics, and report on them by 
dispatching Audit Events

For example, given the hypothetical scenario where we want to detect the situation
where someone is repeatedly trying to log in via ssh, and take some action when a
certain number of failed logins were attempted.

A Correlator Logic Module would process all log entries from sshd, and maintain a map
of failed attempts per source address within a certain time period. When this number
exceeds the maximum allowed, it would create and dispatch a custom event that
included the source IP address.

### Event Listeners

Event Listeners are instances of python classes whose process_event method gets called
with every event dispatched by the Correlator Engine. In that method you can decide what
action to take, if any.

There are 2 integrated event listeners that both the log file processor and syslog server
use:
 - LogbackListener: Logs all events to the python log.
 - CSVListener: Writes audit events to CSV files

Additional listeners may be created for custom actions. For example, in the case of
the ssh failed login detection described above: A new listener would be created that
ignores all events except for that custom event. When it is received, it adds a temporary
rule to the firewall to block that IP address temporarily.

### Event System

There are several predefined Events that can be used or subclassed:
ErrorEvent, WarningEvent, NoticeEvent, and AuditEvent.

#### Standard events

The standard Event can contain quite a bit of information:

- Descriptive summary
- Data block - list of key/value pairs
- Timestamp
- The original log record (if applicable)
- System - source of the event
- optionally a text/html message generated bv mako
- Is this warning, error, or informational message

the ErrorEvent, WarningEvent, and NoticeEvent are subclasses of a standard Event. They
set their own properties to reflect the severity. 

#### Audit events

Audit Events are used to record when something noteworthy happens. They often will end up
as a record in an audit table.

To use Audit Events, you need to create a custom event class based on AuditEvent. Create it
by supplying a string identifier and the attributes that describe the event.

See Module.capture.py - CaptureStatsEvent for an example.

To continue with our example of the ssh failed login detection:

- Make the custom event described above a subclass of AuditEvent. Create it with the
following parameters:
  - An identifier of 'threshold-exceeded'
  - The data of timestamp='xx', address='x.x.x.x'
- Create a new custom event LogonEvent. Add logic to the Correlator Logic Module to dispatch
this event every time someone successfully logs on. Create it with the following parameters:
  - An identifier of 'logon-success'
  - The data of timestamp='xx', address='x.x.x.x', userid='userid'

This would result in two audit streams: threshold-exceeded, and login-success.

- These could be written as records in individual CSV files or database tables (eventually).
- **threshold-exceeded** would have a row containing the timestamp and remote address for every
potential intruder detected.
- **login-success** would have a row that contained the user id in addition to the timestamp and
remote address for every successful ssh login.

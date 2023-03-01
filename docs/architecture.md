# Architecture

The original vision was a syslog server / log processing system that would dynamically scan for both system and user
defined logic modules and event handlers written in python which could be configured, enabled, and disabled in 
real-time via configuration.

It's not there yet. The purpose of this library is to grow to be able to build such a system.

## The front-end engine

The front-end engine is responsible for reading log data and forwarding it through one or more logic modules for
processing. 

Support for, and a reference implementation of, a server that supports listening for and processing syslog data over
the network is included. Support is included for log files as well, but there is no reference implementation.

The operation of the front end is conceptually simple. It is responsible for consuming log data, modelling each record
as a python object, and dispatches these objects to one or more logic modules for processing. Processing consists of
record filtering, correlating, statistics gathering, and event dispatching.

## Modules 

As stated above, logic modules perform record filtering, correlating, statistics gathering, and event dispatching. They
would typically either handle one process or a group of related processes. 

They:

- Maintain and report on statistics 
- Keep state to correlate log events for a higher level of business intelligence
- Dispatch events in response to detected situations.

There is one system module provided: Report. It simply dispatches a notice event for every log record, as well 
as collecting some basic statistics. This module coupled with the Logback event listener is a stack that will simply
read records from the source, and output a summary of each one to the console, via python logging. In fact, 
when you run the reference server in this distribution without the --sshd option, this is the exact stack that is
running.

## Event listeners

An event listener is a python method that gets executed with every dispatched event. This method can take a custom
action when it receives an event that it is interested in. It is the duty of the event listener to ignore events that
it is not. Multiple event listeners can be in use concurrently. All registered listeners receive all dispatched
events. It is the duty of the event listener to ignore events that it is not interested in.

There is one event listener currently shipped with Correlator, the Logback Listener. This simply
logs all events to the python log, and at least in the case of the provided CLI utilities, the console.

## Events

Events are dispatched from the front-end engine or one of its modules. They are modeled as python objects and
are instances of Correlator.event.Event or a subclass.

Standard event types are supplied to provide appropriate default actions. For example, any custom event
dispatched is a subclass of ErrorEvent will generate a python log entry with a severity of error when
being handled by the Logback listener.

## Standard events

The standard Event can contain quite a bit of information:

- Descriptive summary
- Data block - list of key/value pairs
- Timestamp
- The original log record (if applicable)
- System - source of the event
- optionally a text/html message generated bv mako
- Is this warning, error, or informational message

ErrorEvent, WarningEvent, and NoticeEvent are all subclasses of Event. To reiterate a point above, unless there is a
good reason not to, all non-audit type events should extend one of these standard event classes. 

## Audit events

Audit events are dispatched in response to something noteworthy happening, and have a defined data schema. This makes
these suitable to use as audit records as they can map easily to a CSV row, or database table.

All audit events are custom event classes that extend AuditEvent. An identifier and a list of data fields that will
be present in each event must be provided in the class defition.

See Correlator.sshd.SSHDLoginEvent for an example.

## Correlator stack

As described above in "It's not there yet", developing modules or handlers needs to start with a custom
server script.

Central to doing that is the concept of a correlator stack. A configured list of modules and event handlers together
is known as a stack. Even though there may be many logic modules and event handlers available to the system, they
should not always be active. 

For the SIEM example demonstrated in [OpenSSH login module](sshd.md), the stack would be:

- Modules: sshd
- Handlers: logback

This is the relevant code snippet from Correlator.syslog_server:

```python
    processor = EventProcessor()
    processor.register_listener(LogbackListener())

    # Setup list of logic modules

    modules = []

    # Add all modules specified on the command line

    if cmd_args.sshd:
        modules.append(SSHD(processor))

    # If any weren't added,add the Report module

    if not modules:
        modules.append(Report(processor))
```

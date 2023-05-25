# Architecture

The vision is a log data processing system that is easily customizable by developing analysis and event handling logic
in python, that the system could dynamically import during startup. 

It's not there yet. This projects purpose is to build that system.

## The front-end engine

The front-end engine is responsible for reading log data and forwarding it through one or more logic modules for
processing. 

Support for, and a reference implementation of, a server that supports listening for and processing syslog data over
the network is included. Support is included for log files as well, but there is no reference implementation.

The operation of the front end is conceptually simple. It is responsible for consuming log data, modelling each record
as a python object, and dispatches these objects to one or more logic modules for processing. Processing consists of
record filtering, correlating, statistics gathering, and event dispatching.

## Logic Modules

*Todo: find better name!*

Logic modules perform record filtering, correlating, statistics gathering, and event dispatching. They
would typically handle detecting a single process, or group of related processes.

For example, the OpenSSH login module included watches log events generated from OpenSSH for significant login events.

Logic modules:

- Maintain and report on statistics 
- Keep state to correlate log events for a higher level of business intelligence
- Dispatch events in response to detected situations.

There is one system module provided: Report. It simply dispatches a notice event for every log record, as well 
as collecting some basic statistics. This module coupled with the Logback event listener is a stack that will simply
read records from the source, and output a summary of each one to the console, via python logging. In fact, 
when you run the reference server in this distribution without the --sshd option, this is the stack that is
running.

## Event listeners

An event listener is a python method that gets executed with every dispatched event. This method can take a custom
action when it receives an event that it is interested in. It is the duty of the event listener to ignore events that
it is not. Multiple event listeners can be in use concurrently. All registered listeners receive all dispatched
events. It is the duty of the event listener to ignore events that it is not interested in.

There is one event listener currently shipped with Correlator, the Logback Listener. This simply
logs all events to the python log, and at least in the case of the provided CLI utilities, the console.


## Stack

The concept of a Correlator Stack is something that will be fleshed out later in this projects lifecycle, but I do
mention it from time to time. 

A Correlator Stack is a combination of logic modules, event handlers, and associated filter logic to implement an
application (such as the included SIEM sample application)

In the future, the stack definition will exist in a configuration file and will be able to be named. For example,
The sample SIEM application included could be called simple-siem and include:

- OpenSSH login module
- Log, email, and sms handlers
- Filter logic to determine which events warrant which handlers


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
be present in each event must be provided in the class defintion.

See Correlator.sshd.SSHDLoginEvent for an example.

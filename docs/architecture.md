# Architecture

The original vision was a syslog server / log processing system that will dynamically scan for both system and user
defined logic modules and event handlers, which could be configured, enabled, and disabled in real-time buy using a
configuration file.

It's not there yet.

A configured list of modules and event handlers together is known as a stack. To implement a custom stack, you currently
must create your own server. This is straightforward by using Correlator.syslog_server as the base. This is the part of
the server that creates the stack, and would need to be customized with either (or both) of your modules and event
listeners.

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

### The front-end engine

The front-end engine is responsible for reading log data and forwarding it through one or more logic modules for
processing. 

Support for, and a reference implementation of, a server that supports listening for and processing syslog data over
the network is included. Support is included for log files as well, but there is no reference implementation.

The operation of the front end is conceptually simple. It is responsible for consuming log data, modelling each record
as a python object, and dispatches these objects to one or more logic modules for processing. Processing consists of
record filtering, correlating, statistics gathering, and event dispatching.

### Modules 

As stated above, logic modules perform record filtering, correlating, statistics gathering, and event dispatching. They
would typically either handle one process or a group of related processes. 

They:

- Maintain and report on statistics 
- Keep state to correlate log events for a higher level of business intelligence
- Dispatch events in response to detected situations.
- Standard Error, Warning, or Informational event classes are provided that have appropriate default behavior.
- Audit event class is also provided. These are events that contain a defined data dictionary. They are suitable 
for recording in a table, as their structure is pre-defined.


There is one system module provided, Report, that simply dispatches a notice event for every log record. It also
collects basic statistics. Coupled with the Logback event listener is a stack that will simply output a summary of the
record to the console, via python logging. In fact, when you run the reference server in this distribution without the
--sshd option, this is the exact stack it is running.

### Event listeners

An event listener is python code that listens for events that it is interested in and takes a specific action when
it receives them. Multiple event listeners can be in use concurrently. In that case, all registered listeners will
receive all events. It is the duty of the event listener to ignore events that it is not interested in.

There is currently one event listener shipped with the Correlator system, the Logback Listener. This simply
logs all events the console.

### Events

Events are dispatched from the front-end engine or one of its modules. They are modeled as python objects and
are instances of Correlator.event.Event or a subclass.

Standard event types are supplied to provide appropriate default actions. For example, any custom event
class that subclasses the Error event will generate a python log entry with a severity of error when
being handled by the Logback listener.

#### Standard events

The standard Event can contain quite a bit of information:

- Descriptive summary
- Data block - list of key/value pairs
- Timestamp
- The original log record (if applicable)
- System - source of the event
- optionally a text/html message generated bv mako
- Is this warning, error, or informational message

ErrorEvent, WarningEvent, and NoticeEvent are all subclasses of Event. System listeners have default actions based
on the severity, so unless there is a good reason not to, all non-audit type events should extend one of these
standard event classes.

#### Audit events

Audit events are dispatched in response to something noteworthy happening. 

To use audit events in your modules, they must be defined as a custom class which uses the Event class as its
super. An identifier and a list of data fields that will be present in each event must be provided in the custom by the
dispatching code.


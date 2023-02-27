# Architecture
 
This library provides a framework to create log data processing systems. A reference server is provided
both as an example and a development tool.


### The engine

The  engine is responsible for reading the log data and feeding it through
one or more Logic modules for processing, as well as requesting and reporting
on statistics collected by all running modules. 

### Modules 

Modules process log records, collect statistics, and dispatch events. One module
handles related log events. It is possible to have several modules running, providing insight into various processes
at the same time.

Modules:

- Are python classes
- Maintain and report on internal statistics 
- Can maintain state to correlate log events for a higher level of business intelligence
- Dispatch Error, Warning, or Informational events to be logged and possibly acted on
- Dispatch Audit events: Events with guaranteed data suitable for recording (for example, a database/csv file row)

There is one system module provided, Report, that simply dispatches a notice event for every log record and collects
basic overall statistics. Coupled with the lockback event listener, this will simply output a summary of the record to
the console, via python logging.

#### Example custom module:

(Describe sshd-module here)

A module could be created to process events from a secure shell server running on Linux.
It could listen for both successful and failed login attempts, keeping a running total of both
for statistical purposes. It could keep track of the number of failed attempts per source address
within a certain time period. When this number exceeds a predetermined threshold, it could dispatch a custom event
called (for example) SSHLoginTriesExceeded.

The event handler for that event could execute a command that would add that source IP address to a temporary
firewall block list, for example.

The daily statistics from this module could be (easily, at least):
  - Total number of successful ssh logins
  - Total number of failed ssh logins
  - Total number of failed ssh logins that don't have a successful login (today)
  - Total number of source addresses that exceeded X ssh login attempts and got blocked

### Events

Events are dispatched from the Correlator engine or one of its modules. They are implemented as
python classes and be extended to provide additional functionality.

#### Standard events

The standard Event can contain quite a bit of information:

- Descriptive summary
- Data block - list of key/value pairs
- Timestamp
- The original log record (if applicable)
- System - source of the event
- optionally a text/html message generated bv mako
- Is this warning, error, or informational message

the ErrorEvent, WarningEvent, and NoticeEvent are derived from events with the appropriate properties set.

#### Audit events

Audit events are dispatched in response to something noteworthy happening. They often will end up
as a record in a csv file or a database table.

To use audit events in your modules, they must be defined as their own class, which subclasses an audit event. An
identifier and a list of data fields that will be present in each event must be provided in the custom by the
dispatching code.

These events will often end up as records in a csv file or a database table.

See Module.capture.py - CaptureStatsEvent for an example.

### Event listeners

An event listener does just that - its python code that can take action in response to an event. All events are
currently dispatched to all handlers. It is up to the handler itself to filter the events to just the ones that
it is interested in, if desired.

There are 2 system event listeners that are used by the provided scripts and can be used in your code:

 - **LogbackListener:** Logs all events to the python log.
 - **CSVListener:** Writes audit events to CSV files

Additional listeners may be created for custom actions. For example, in the case of
the **Theoretical example of a module** example in the **Logic Modules** section:

A new event listener could be created that would ignore all events except for the custom event SSHLoginTriesExceeded.
When processing *that* event, it could add a temporary rule to the firewall to block the source IP address.
If that event's superclass is one of the standard event classes, then other listeners may also handle that event. For
example, if the SSHLoginTriesExceeded is a subclass of ErrorEvent, then this will also get logged to the python
error log.

## Limitations

CLI scripts hard coded with module/handlers stack.
This is not resilient to exceptions at all.

## To do

- Regex evaluation / optimization
- Think of overall documentation strategy
- Add capability for listeners to register criteria for event filtering at instantiation time.
- Exception handling
- state Persistence

# Event system

The Correlator Event system consists of:



## Events

The front-end engine or one of its modules react to noteworthy situations by dispatching events that can be received
and acted on by event handlers.

They are modeled as python objects and are instances or children of of Correlator.event.Event.

Standard event types are supplied to provide appropriate default actions. For example, any custom event
dispatched is a subclass of ErrorEvent will generate a python log entry with a severity of error when
being handled by the Logback listener.

## Standard events

The standard Event can contain quite a bit of information:

- Descriptive summary
- Data block - list of key/value pairs
- Timestamp
- System - source of the event
- optionally a text/html message generated bv mako
- Is this warning, error, or informational message

ErrorEvent, WarningEvent, and NoticeEvent are all subclasses of Event. To reiterate a point above, unless there is a
good reason not to, all non-audit type events should extend one of these standard event classes. 

### Usage
### ::: Correlator.Event.core.Event
    options:
        show_source: false
        show_root_heading: true


## Data events

Data events are also dispatched from the front-end engine or one of its modules, but they differ with standard
events in that they follow a simple data schema. 

This schema defines the data to contain:
- A flat collection of key/value pairs. There can be no additional structure beyond this.
- A list containing all the field names (key values).

Each event must contain a key/value pair in the payload for every field in field name list (and no more).

This makes these events suitable for inserting into a database table. In addition, field positions may be honored
by event handlers where this is important (the CSV handler for example).

### Usage
### ::: Correlator.Event.core.DataEvent
    options:
        show_source: false
        show_root_heading: true

## Event handlers

Event handlers are python objects that extend the Event.core.EventListener base class to take a custom action. When a 
Correlator module (or the Correlator system itself) dispatches an event, it forwards it to all registered event
handlers. Each handler must decide whether to take action based on the contents of the event.

There are several event handlers that ship with this distribution:

- logback:
    - writes events to the python log
- CSV:
    - Saves the data in audit events to rows in a CSV file
- Email:
    - Sends HTML or plaintext email via Mako templates driven from data within the event.
- SMS:
    - Twilio interface to send SMS messages with data from within the event

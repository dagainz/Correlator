# Event system

The Correlator Event system consists both of events, which signify that something noteworthy has happened,
and event handlers, which can take action in response to event.

The front-end engine or any of the active modules can dispatch events.

## Events

The front-end engine or one of its modules react to noteworthy situations by dispatching events that can be received
and acted on by event handlers.

They are modeled as python objects and are instances or children of of Correlator.event.Event.

Events will not typically get instantiated directly by client code, instead a preferring to use one of its subclasses.
This is the base object that events handlers will see however, so it is necessary to understand its structure.

Events contain:

- Timestamp
- Event type: Currently Standard or Dataset
- Event Status: Error, Warning, Informational
- System ID: Source of the event
- Event ID: Event identifier, if event type is Dataset
- Event description: String description of the event
- Summary: String summary
- Payload: a python dict with arbitrary data, to be used in event handlers

ErrorEvent, WarningEvent, and NoticeEvent are all subclasses of Event which set the appropriate status.

## Event docs from the code

### ::: Correlator.Event.core.Event
    options:
        show_source: false
        show_root_heading: true

## Event handlers

Event handlers extend Event.core.EventListener base class to take custom actions in response to events. When a 
Correlator module (or the Correlator system itself) dispatches an event, it forwards it to all registered event
handlers. Each handler must decide whether to take action based on the contents of the event.

There are several event handlers that ship with this distribution:

- logback:
    - writes events to the python log
- CSV:
    - Saves the data in data events to rows in a CSV file
- Email:
    - Sends HTML or plaintext email via Mako templates driven from data within the event.
- SMS:
    - Twilio interface to send SMS messages with data from within the event

# Correlator

The intention of this project is to provide a system that read and take action on log records. This action may be as simple as logging something to the python log or adding a record into a CSV file or database table, but it could also perform tasks such as generate a ServiceNOW issue or add a temporary rule into a firewall in response to something that was detected in the log.

## Architecture

### The correlator engine

This is the bulk of the system and consists of a front end that reads log records from the source, and passes them to one or more Correlator logic modules for processing.

The engine or any Correlator logic module's response to various situations is to generate and dispatch an event when something noteworthy happens. 
 
### Correlator logic module (Python class)

This is a module that has logic to understand a particular use case or scenario. 

For example, imagine the scenario where you want to detect when someone is trying repeatedly to log in to various accounts via ssh, so that their IP address can get added to a blocklist on a firewall. This module could keep track of the number of failed attempts per source address and dispatch an event with the source IP when it passes some threshold.

### Event Processing

This part of the system is responsible for processing and reacting to events dispatched by the correlator engine. It accomplishes this by distributing the generated events to one or more Event Listeners to give them the opportunity to take action.

### Event Listeners (Python class)

Event Listeners are python classes that can decide to take action on events. A new event listener class can be created to take custom action in the response to any events.

There are 2 integrated event listeners: LogbackListener and CSVListener. LogbackListiner simply logs the events to the python log, while CSVListener writes audit events to CSV files.

### Event System

There are a handful of ready to use or subclass standard events such as ErrorEvent, WarningEvent and NoticeEvent. It is simple to subclass these and add more detail.

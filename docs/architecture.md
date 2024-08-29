# Architecture 

Although the code in this repository forms a fully running system, in its present state its real-world use is limited:

1. The only included logic module is OpenSSH.  Unless all you will ever want is to monitor OpenSSH for login attempts,
logic module development is necessary.
2. The included event handlers are very basic and are suitable for testing, demonstration, and to serve as examples
to develop real handlers.

**This project's current purpose is to provide the framework to build a custom log monitoring system in python**, hence
its manifestation as a python package.

### Programmable components

There are 3 main functional areas that have been designed to be implemented or extended with python:

#### The front-end

The front-end is responsible for retrieving and parsing log records from the source and distributing them to
one or more logic modules for analysis.

#### Logic modules

Logic modules detect noteworthy incidents by detecting patterns within log records and dispatching
events into the event stream in response.

#### Event handlers

Event handlers listen to the event stream and potentially take action in response.

### The supporting components

At the heart of the system that ties the programmable components together is a pair of configuration systems:

#### The configuration store

The configuration store is a memory based table that contains items that each part of the system use to affect
their run-time behavior. Values for these items can be set with the application configuration described in the next
section, or overriden by command line options. The configuration store helps eliminate common errors (like typo's) by:

- Ensuring the configuration items exist, as they must be pre-defined by the module or component.
- Checking for valid data-types.

  To show the details of the configuration store while using the syslog server, you can:

  - Run the server in debug mode using the --d command line argument. This will dump the contents of the
  configuration store as part of its start up, before processing packets.
  - Run the server with the --config comnmand line argument. This will dump the contents of the 
  configuration store and then exit (try: syslog_server --app ssh-email --config).

- **The application config** defines *Correlator Applications* in a configuration file. Applications
define the behavior of a running Correlator instance. An application consists of:
    - One or more logic modules, plus their configuration values in the configuration store
    - One or more event handlers, plus their configuration values in the configuration store 
    - For each instance of an event handler, a python expression that filters the events that the handler should take
action on. For example, filters could be used to send all warnings and errors via email, but only errors of a particular
type via sms. 

      Given the filter expressions described above, and the fact that the application config system dynamically loads
python
modules, new Correlator applications can be developed and run without modifying the Correlator source code. Quite a bit
of the systems behavior can be modified by configuration only. 


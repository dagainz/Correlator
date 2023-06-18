# Correlator

A log event processing system written in Python.

## Overview

Correlator is a proof-of-concept system that can read and process log data by forwarding log records through one or more
*modules* that detect patterns in log data, and, by using an event system, respond to detected situations in various
ways.

Functionality and scaffolding is provided to process log data in real time over the network as well as after-the-fact
by reading and processing log files. 

## High level features

- Analysis interface promotes the creation of independent modules that *understand* one or one set of processes.
- Event system separates the analysis and event logic.
- Event handler interface promotes the creation of individual event handlers that perform one type of action.
- Layer multiple modules and event handlers together in a stack to implement a Correlator application.
- RFC 5424 compliant syslog server with packet capture and replay
- Capture file utility to helps manage captured syslog data
- A single module is included: *OpenSSH login*, that combined with event handlers demonstrate a simple SIEM.

## Requirements

- Python 3.10
- Possibly a Unix like environment. Development has been on macOS, but I do expect it work on other unix like systems.
It has not been tested on Microsoft Windows.

## Limitations and known issues

- Lots. This is a proof of concept, and early in the development lifecycle. Bugs are plenty and things change often.
- Single thread.
- Virtually no exception handling.
- The syslog server services a single connection.
- This has yet to see any full time use, although this will change soon, after this release
- The event system has no retry capability. Its fire-and-forget.
- Development sways between the Correlator Core, Syslog Server, Logfile processor, and a private implementation
of Correlator customized to monitor a proprietary product. Some parts are lagging behind others.



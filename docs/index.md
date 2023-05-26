# Correlator

A log event processing system written in Python.

## Overview

Correlator is a Python library and collection of utilities that collectively facilitate the creation of log event
processing systems. Functionality and scaffolding is provided to create systems that process log data in real time
over the network as well as after-the-fact by reading and processing log files. 

## Features

- Pure Python framework to develop systems that analyze and take action in response to system logn event data.
- Separate analysis and event interfaces
- RFC 5424 compliant syslog server with packet capture and replay
- Capture file utility to helps manage captured syslog data
- Ships with a sample application, *OpenSSH login module* that combined with out-of-the-box event handlers demonstrate a 
simple SIEM.

## Requirements

- Python 3.10
- Possibly a Unix like environment. Development has been on macOS, but I do expect it work on other unix like systems.
It has not been tested on Microsoft Windows.

## Limitations and known issues

- This is early in the development lifecycle. Bugs are plenty and things change often. This has yet to see any full time
use, although this will change soon.
- The event system has no retry capability. Its fire-and-forget.
- Development of the log file processing front end is slightly behind the syslog server front end, which likely will
introduce (maybe not so) subtle bugs.




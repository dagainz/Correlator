# Correlator

A log event processing system written in Python.

## Overview

Correlator is a Python library and collection of utilities that collectively facilitate the creation of log event
processing systems. Functionality and scaffolding is provided to create systems that process log data in real time
over the network as well as after-the-fact by reading and processing log files. 

## Features

- Pure Python framework to develop systems that correlate, report on, and take action in response to system log
event data. 
- The framework provides an analysis as well as event interfaces to promote separating detection and correlation from
event handling logic.
- RFC 5424 compliant syslog server with packet capture and replay
- Capture file utility to helps manage captured syslog data

## Sample application

- Provided OpenSSH login logic module combined with out-of-the-box event handlers demonstrate a simple SIEM application.

## Requirements

- Python 3.10
- Possibly a Unix like environment. Development has been on macOS, but I do expect it work on other unix like systems.
It has not been tested on Microsoft Windows.

## Limitations and known issues

This is not an exhaustive list

- This is early in the development lifecycle. It does not yet do much, and bugs are plenty.
- The event system has no retry capability. Its fire-and-forget.
- There is no persistence. Modules must keep state for correlation and statistics gathering/reporting. Without
persistence, if the server process is stopped or restarted for any reason, all state will be lost.
- The server is functional but not reliable for real operational use.



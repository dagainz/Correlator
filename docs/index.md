# Correlator

The log event processing system written in Python.

## Overview

Correlator is a Python library and collection of utilities that collectively
facilitate the creation of log event processing systems. Functionality and scaffolding is provided to create systems
that process log data in real time over the network as well as after-the-fact by reading and processing log files.

## Features

- Pure Python framework to develop systems that correlate, report on, and dispatch events based on system log records
and take custom actions in response to any of these events.
- CLI based syslog server with packet capture and replay
- CLI capture tool that helps manage captured syslog data
- OpenSSH login logic module reports and alerts on ssh login attempts. This demonstrates a simple SIEM.

## Requirements

Python 3.10+
This was developed on macOS, and I expect it work on any unix like system. It has not been tested on Microsoft Windows.

## Limitations and known issues

This is not an exhaustive list

- This is early in the development lifecycle. It does not yet do much, and bugs are plenty.
- The event system has no retry capability. Its fire-and-forget.
- No state persistence. Modules must keep state for correlation and statistics gathering/reporting. Without
persistence, if the server process is stopped or restarted for any reason, all state will be lost.
- The server is functional but not reliable for real operational use.



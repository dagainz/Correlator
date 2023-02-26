# Correlator

The log event processing system written in Python.

## Overview

Correlator is a Python library and collection of utilities that collectively
facilitate the creation of log event processing systems. Functionality and scaffolding is provided to create systems
that process log data in real time over the network as well as after-the-fact by processing log files.

## Features

- Pure Python framework to develop systems that Correlate, report on, and dispatch events based on system log records
and take custom actions in response to any of these events.
- Syslog server with packet capture and replay
- CLI to help manage captured syslog data
- Sample logic module to report and alert on ssh login attempts.

## Requirements

Python 3.10+

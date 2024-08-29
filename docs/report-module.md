# Module: Report

## Overview

This module simply dispatches Notice events for every log record processed.

It also counts and reports on basic statistics.

This is the module that gets used in the stack when using the --report-only option on any CLI.

## Configuration parameters

There are no configuration parameters that affect the behavior of this module.

## Dispatched events

### NoticeEvent

### ReportStatsEvent (Audit Event)

This event is dispatched whenever module statistics are called.

| Attribute | Value               |
|-----------|---------------------|
| timestamp | timestamp of event  |
| start     | Session start       |
| end       | Session end         |
| duration  | Session duration    |
| size      | Total size in bytes |

## Persistence store usage

This module only counts statistics, so it makes minimal use of the persistence store.

## Maintenance and statistics

Nothing, other than the statistics event above.

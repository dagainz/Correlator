# The logfile processor front end

This front end is responsible for reading a logfile into records and forwarding them through the stack for processing.

Like the other front ends, the logfile processor is implemented as a python class. Unlike the other front ends,
it is not usable without creating a class that can parse the particular log file that you are interested in.

For this reason, there is currently no reference implementation of a logfile processor included with this distribution.

## Persistence store

The persistence store is not available in this front end.

## Timer handler methods

This frontend does not support timer handler methods.

## Configuration parameters

This front end has no configuration parameters.

## Usage

There is no plan currently to formalize or overly document internals at the time. For now, the docstrings will have to
do.

### ::: Correlator.logfile.LogfileProcessor
    options:
        show_source: false
        show_root_heading: true

### ::: Correlator.logfile.LogRecord
    options:
        show_source: false
        show_root_heading: true

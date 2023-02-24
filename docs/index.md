# Correlator

The log event processing system written in Python.

## Overview

Correlator is a python library and collection of utilities that collectively
facilitate the creation of log event processing systems.

## Architecture
   
This system has a modular architecture for extensibility. Core logic handles the reading of log records from its source and is responsible to
distributes it to one or more logic modules for processing. The modules dispatch events when
it has detected a pattern in the log data.

Multiple logic modules and event handlers can be running at once. The combination of one
or more logic modules and one or more event handlers describes a *Correlator stack*.



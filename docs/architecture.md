# Architecture
 
This package provides a framework and structure to create log data processing systems. This
is accomplished by leveraging the common code in the library, and writing custom modules that:

- Interpret the log data and dispatch events in response to detected patterns in the data.
These modules are referred to as Logic modules.

- Receive dispatched events to take specific actions. These are event handlers.

Multiple logic modules and event handlers can be in use at the same time. The combination of one
or more logic modules and one or more event handlers is collectively called a *Correlator stack*.


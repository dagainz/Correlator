# The Correlator Stack

This stack is not a stack in the traditional LIFO sense. In ths context, it represents a set of modules, event handlers,
and the associated event filtering logic that together define the operation of a Correlator instance.

This concept is a bit nebulous at the moment, but I do expect to flesh it out in the future, but I do mention it from
time to time, so I felt it deserves mention here.

The stack fits into the overall vision of a fully configurable log processing system that is possible without any 
python. Even when python is required to develop custom modules or event handlers, the system should be able to
dynamically import, configure, and instantiate the custom code *without writing python*.

This is one of the final pieces that will move this from a python library to a self-contained application.

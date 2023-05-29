# Frontend engine

The front-end engine is primarily responsible for reading log data and forwarding it through all the logic modules in the
stack.

It also:

- Is responsible for triggering module's *timer handler* methods at the appropriate time
- Calls the module's statistics gathering and resetting methods
- Can send its own events, and generate its own statistics
- Acts as the CLI UX for the shipped CLI utilities

There are two front ends classes that ship with this distribution:

- Syslog server
- Logfile processor

It possible that there will be other front end support classes in the future. For example:
- Message queue client
- Server to handle output from custom log-gathering server agents.

**Note**:

- There is functionality buried within the syslog server code that should be moved into its own utility classes
for use in other front-end code (such as the persistence store).
- Primary development (and feature development) has been within the syslog server, thus the logfile processor is behind,
and likely has bugs and can have weird behavior at times.
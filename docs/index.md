# Correlator

Correlator is a log processing system written in Python. 

It consumes and processes log data looking for patterns, and taking specific actions when they occur. It provides an
interface to write both custom detection and/or action logic in python, which it can dynamically import.

out-of-the-box functionality includes:

- RFC 5424 compliant TCP syslog server processes syslog records received from a remote system. Also has the
ability to capture received syslog packets to a file, and to use these capture files as input.
- An OpenSSH *logic module*: Detection logic that looks for patterns, such as **Successful login** in OpenSSH's
log stream, and dispatch *events* in response.
- Several *event handlers*: action logic that take action when these events occur.
  - Email: Generates an email from a template using mako, and send via SMTP.
  - CSV: Writes event data to rows in a csv file.
  - SMS: Sends a basic SMS via twilio.

And more!

---

### Helpful documentation links:


- [quick start](quickstart.md) outlines a couple methods to get up and running quickly.
- [Architecture](architecture.md) discusses the overall architecture in more depth.
- [Implementation](implementation.md) has more detail around the functionality in this release.

## Requirements

- Python 3.10
- A Unix like system, or Docker.

## Limitations and known issues

As *this is a currently a proof of concept*, there are many. Such as:

- Single thread. An event handler blocking forever will halt the system.
- Limited exception handling, making the system fragile.
- The syslog server services a single TCP connection.
- The event system has no retry or even audit capability. Its fire-and-forget.
- The Application configuration file currently is in JSON format. This is less than ideal for humans, but it maps easily
to python data structures.
- Correlator output goes to stdout, making it really only usable for interactive testing purposes.




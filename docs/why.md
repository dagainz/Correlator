## Why?

I've spent a great deal of my career deploying various enterprise software solutions. In that role, I often find myself
pouring over log files 
trying to understand why the system behaved in a certain way. Modern systems can generate log data from many disparate
services and systems. It can be challenging enough tracing a transaction through the system in a development
environment where the amount of *noise* can be controlled, unlike busy production environments.

One particular time, I was troubleshooting a customer issue where a transaction through their system was silently
failing. As we needed to identify the failed requests but the failure message in the log file did not indicate which
request failed. Several records had to be correlated together and tied to a transaction, with information pulled from
each.

After trying for a while to visually correlate the log data to get this information, I decided to write a *quick and
dirty* script to parse the log file, perform the correlation, and report on ALL of the transactions.

It provided the intelligence that the customer was looking for, plus additional valuable metrics. However, I felt
that we could do better than detecting and reporting when problems happened in the past. That lead to the addition of a syslog server
front end that drove the same analysis logic. After configuring the system to forward log events to the syslog
server, I could now detect events in real time over the network as well as on historical events by processing logfiles.
All using the same correlation, detection, and event dispatching logic.

I've always been interested in network, server, and application management. I've worked with several open source and
commercial monitoring systems and have a few greenfield implementations under my belt. Having a data center background
I am often surprised that with many complex software deployments log data goes virtually unmonitored, especially with
the amount of high value data that is often contained within.

This project scratches an itch that I've had for while, which was demonstrating a proof of concept of a management
system that can provide context aware remote real-time monitoring capability to a mission-critical deployment of
security software through the existing logging system.


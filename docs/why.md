## Why?

One of my primary roles is designing and deploying enterprise security solutions. In that role, I am often pouring over
log files to try to understand why the system behaved in a certain way. With log data coming from several services
It can be challenging enough tracing a transaction through the system in a development environment where the amount of 
*noise* can be controlled, unlike a busy production environment where log data from several concurrent processes are 
multiplexed together, and often spread across application instances or containers. 

One particular time, I was troubleshooting an issue with the system where a transaction was silently failing.
As usual, the details were in the log file. Not only did we need to know when it happened, but also to determine
a way to identify the failed request, so that the failed transactions could be re-run. To accomplish this, several
records needed to be correlated together and tied to the same transaction, with information pulled from each.

After trying for a while to visually correlate the log data to get this information, I decided to write a log file 
parser that would perform the correlation and automate the process. I wrote the script, keeping the mechanics of log
record handling separate from the analysis and action logic, so that it could easily be extended to solve other problems.

It provided the intelligence that the customer was looking for, plus some additional valuable metrics. However, I felt
that we could do better than detecting when problems happened in the past. That lead to the addition of a syslog server
front end that drove the same analysis logic. After configuring the system to forward log events to the syslog
server, I could now detect events in real time over the network as well as on historical events by processing logfiles.
All using the same correlation, detection, and event dispatching logic.

I've always been interested in network, server, and application management. I've worked with several open source and
commercial monitoring systems and have a few greenfield implementations under my belt. Having a data center background
It always bothered me that our customers implementations often do nothing with the log data that our product produces.
This project scratch the itch that I've had for while, which was demonstrating a proof of concept of a management
system that can provide context aware remote real-time monitoring capability to a mission-critical deployment of
security software through the existing logging system.


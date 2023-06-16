## Why?

It's for a couple of reasons.

### #1: Personal development

The first is for my personal development. I learned python at work. I really enjoy it. There, however, we work within
the confines of a proprietary framework that doesn't give much of an opportunity to work within other parts of python
such as, for example, packaging and project structure. 

I wanted to start something from scratch, and practice some of these, and other things.

### #2: Because this stuff is cool

#### The pre-story

I've spent a great deal of my career deploying various enterprise software solutions. In that role, I often find myself
pouring over log files trying to understand why the system behaved in a certain way. Modern systems can generate log
data from many disparate services and systems. It can be challenging enough tracing a transaction through the system in
a development environment where the amount of *noise* can be controlled, unlike busy production environments.

#### The story

One time a short while ago, I was troubleshooting a customer issue where a transaction through their system was silently
failing. The answer was in the log, but it was not obvious. Several records had to be correlated together and tied to a
transaction, with information pulled from each. After that, the information could be used to determine if the
transaction was successful. We needed to identify which of the several hundred or thousand requests failed, so they
could be resubmitted.

After trying for a while to visually correlate the log data to get this information, I decided to write a script to 
parse the log file, perform the correlation, and report on ALL of the transactions, failed or otherwise.

It provided the intelligence that the customer was looking for, plus additional valuable metrics. However, I felt
that I could do better than detecting and reporting when problems happened in the past. That lead to the addition of a
syslog server front end that drove the same analysis logic. After configuring the system to forward log events to the
syslog server, I could now detect events in real time over the network as well as on historical events by processing
logfiles. All using the same correlation, detection, and event dispatching logic.

**So it was born**

#### A bit about me

I've always been interested in network, server, and application management. I've worked with several open source and
commercial monitoring systems and have a few greenfield implementations under my belt. Having a data center background
I am often surprised that with many complex software deployments log data goes virtually unmonitored, especially with
the amount of high value data that is often contained within.



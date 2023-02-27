## Why?

One of my day jobs is designing and deploying enterprise security solutions. These systems can continuously produce
large quantities log data. Having a data center background I'm often surprised at how much high value operational
information buried within logs like these goes largely unreviewed. 

The problem is compounded by the fact that one business process through the system can produce quite a bit of log
data. On a busy system, it can make it difficult to visually correlate the log data to identify which records belong
to the process in question.

After one particularly grueling log analysis session troubleshooting a customer issue, I had an idea to write a simple
log file parser that read and correlated log entries to identify and report on problems with a certain business process. 

I wrote the script, keeping the mechanics of reading and reporting separate from the analysis logic, so that it
could be reused to detect and report on other areas of interest.

It provided the intelligence that the customer was looking for, but I felt that we could do better than detecting when
these things happened in the past. That lead to adding a syslog server front end that drove the same analysis
logic. I could now report on historical events by processing logfiles and detect events in real time over the network
via syslog. All using the same correlation, detection, and event dispatching logic.

So with this project I'm starting to scratch an itch that I've had for a while, which is to *do something* with all this
data we're throwing out. It's already solved a business problem of mine and provided valuable business intelligence,
and I hope to use it for more.

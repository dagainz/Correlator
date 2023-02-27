## Why?

For my day job I design and deploy enterprise security solutions. Having a data center background I'm often surprised
at how much high value operational information buried within system log data goes virtually unreviewed unless it's being
used to troubleshoot current operational issues. Even then, a single business process can result in several log entries
from various parts of the system, making it difficult to manually/visually correlate.


After one particularly grueling log analysis session troubleshooting a customer issue, I had the idea to write a simple
log file parser that read and correlated log entries to identify and report on problems with a certain business process. 

I wrote the script, keeping the mechanics of reading and reporting separate from the analysis logic, so that it
could be reused to detect and report on other business processes.

It worked and provided the intelligence that the customer was looking for, but I felt that we could do better
than detecting when these sorts of things happened in the past. That lead to adding a 
syslog server front end that can drive the same analysis logic. I could now report on historical events by processing
logfiles and detect events in real time over the network via syslog, using the same correlation logic.

So with this project I'm starting to scratch an itch that I've had for a while, which is to *do something* with all this
data we're throwing out. It's already solved a business problem of mine and provided valuable business intelligence,
and I hope to use it for more.

## Why?

For my day job I design and deploy enterprise security solutions. Having a data center background I'm often surprised
at how much high value operational information buried within system log data goes virtually unreviewed unless it's being
used to troubleshoot current operational issues. Even then, a single business process can result in several log entries
from various parts of the system, making it difficult to manually/visually correlate.

I've thought about something like this on more than one occasion.

After one particularly grueling log analysis session troubleshooting a customer issue, I had the idea to write a simple
log file parser that read and correlated log entries to identify and report on problems with the business process. 

So I wrote the script, keeping the mechanics of reading and reporting separate from the analysis logic, so that it
could be reused to detect and report on other business processes.

For this particular instance, after-the-fact analysis of the logfile was fine, and even required to be able to analyze
multiple historical logfiles. But the real power lies in real-time analysis, reporting, and alerting. I added a
syslog server front end, driving the same analysis logic. I could now report on historical events by processing logfiles
and detect events in real time over the network via syslog, using the same correlation logic.

So with this project I'm starting to scratch an itch that I've had for a while. It's already solved a business problem
and provided valuable business intelligence, but I feel it can be used for more.

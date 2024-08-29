# Modules

Modules are the heart of this system.

They:

- Provide the logic that understands a problem
- Maintain and report on statistics 
- Keep state to correlate log events for a higher level of business intelligence
- Dispatch events in response to detected situations.

For example, if you wanted to watch for Let's Encrypt! **certbot** messages in the linux log, and send any it finds via
email to an administrator, you would need to develop a module.

This module could:

- watch for log entries such as these:

```
May 21 06:56:01 giganode1 certbot[3267940]: - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
May 21 06:56:01 giganode1 certbot[3267940]: Processing /etc/letsencrypt/renewal/app.thepushors.com.conf
May 21 06:56:01 giganode1 certbot[3267940]: - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
May 21 06:56:01 giganode1 certbot[3267940]: Saving debug log to /var/log/letsencrypt/letsencrypt.log
May 21 06:56:01 giganode1 certbot[3267940]: Failed to renew certificate app.thepushors.com with error: The manual plugin is not working; there may be problems with your exist
ing configuration.
May 21 06:56:01 giganode1 certbot[3267940]: The error was: PluginError('An authentication script must be provided with --manual-auth-hook when using the manual plugin non-int
eractively.',)
May 21 06:56:01 giganode1 certbot[3267940]: - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
May 21 06:56:01 giganode1 certbot[3267940]: Processing /etc/letsencrypt/renewal/thepushors.com.conf
May 21 06:56:01 giganode1 certbot[3267940]: - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
May 21 06:56:01 giganode1 certbot[3267940]: Failed to renew certificate thepushors.com with error: The manual plugin is not working; there may be problems with your existing 
configuration.
May 21 06:56:01 giganode1 certbot[3267940]: The error was: PluginError('An authentication script must be provided with --manual-auth-hook when using the manual plugin non-int
eractively.',)
May 21 06:56:01 giganode1 certbot[3267940]: - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
May 21 06:56:01 giganode1 certbot[3267940]: All renewals failed. The following certificates could not be renewed:
May 21 06:56:01 giganode1 certbot[3267940]:  /etc/letsencrypt/live/app.thepushors.com/fullchain.pem (failure)
May 21 06:56:01 giganode1 certbot[3267940]:  /etc/letsencrypt/live/thepushors.com/fullchain.pem (failure)
May 21 06:56:01 giganode1 certbot[3267940]: - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
May 21 06:56:01 giganode1 certbot[3267940]: 2 renew failure(s), 0 parse failure(s)
May 21 06:56:01 giganode1 certbot[3267940]: Ask for help or search for solutions at https://community.letsencrypt.org. See the logfile /var/log/letsencrypt/letsencrypt.log or
 re-run Certbot with -v for more details.

```

- Build a new transaction in the modules store when encountering a record with a new PID for the first time
- Add to the transaction with every other record with that same PID. If the word 'Failed' appears anywhere, mark the
transaction as in error.
- When we haven't seen a new record in a certain amount of time, dispatch an error or informational event with the
entire message.
- Mark the PID as unused.

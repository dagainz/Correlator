#!/bin/bash

# Script to startup rsyslog before the ssh server to configure the container to forward log events to correlator.

LOGSOCKET=/dev/log
RETRIES=5

function error_exit () {
	echo "** Initialization of rsyslog plus secure shell failed"
	exit 1
}

echo "** Starting rsyslog"

/usr/sbin/rsyslogd -n &

# We want to wait until we have a /dev/log to make sure we catch all
# of sshd's log entries due to a chicken and egg problem.

COUNT=1

while true
do
  echo "** Waiting for log socket ${LOGSOCKET}"
  sleep 1

  if [ -S ${LOGSOCKET} ]; then
        break
  fi
  COUNT=expr`${COUNT} + 1`

  if [ "${COUNT}" -eq "${RETRIES}" ]; then
    echo "** Retry count exceeded (${RETRIES})"
    error_exit
  fi
done

echo "** Starting sshd"

# Create privilege separation directory if it does not exist

if [ ! -d /run/sshd ]; then
 mkdir /run/sshd
fi

/usr/sbin/sshd -D &

echo "** Initialization of rsyslog plus secure shell complete. Waiting for either to exit"

wait -n

echo "** ERROR:One of the daemons have shut down or died with exit code ${$?}"

exit $?

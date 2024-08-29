#!/bin/bash

# "wrapper Script" to start both rsyslog and ssh in a Docker container.

# https://docs.docker.com/config/containers/multi-service_container/

LOGSOCKET=/dev/log
RETRIES=5
rsyslog_pid=""
sshd_pid=""

function error_exit () {

  # Kill any running sshd's or rsyslogd's

  if [ ! -z "${sshd_pid}" ]; then
    echo "DEBUG: Killing sshd"
    kill ${sshd_pid}
    wait ${sshd_pid}
  fi
  if [ ! -z "${rsyslog_pid}" ]; then
    echo "DEBUG: Killing rsyslog"
    kill ${rsyslog_pid}
    wait ${rsyslog_pid}
  fi
	exit 1

  echo "ERROR: $1" 1>&2
}

# Gracefully handle 'docker container stop'

function handle_term () {
  error_exit "Caught sigterm. Shutting down"
}

trap "handle_term" SIGTERM

echo "Starting rsyslog"

/usr/sbin/rsyslogd -n &
rsyslog_pid=$!

# wait for /dev/log

COUNT=1

while true
do
  echo "Waiting for log socket ${LOGSOCKET}"
  sleep 1

  if [ -S ${LOGSOCKET} ]; then
        break
  fi
  COUNT=expr`${COUNT} + 1`

  if [ "${COUNT}" -eq "${RETRIES}" ]; then

    error_exit "Rsyslog startup failed. No ${LOGSOCKET} after ${RETRIES} seconds"
  fi
done

echo "Starting sshd"

# Create privilege separation directory if it does not exist

if [ ! -d /run/sshd ]; then
 mkdir /run/sshd
fi

/usr/sbin/sshd -D &
sshd_pid=$!

echo "Rsyslog & sshd successfully started"

wait -p job_id -n ${sshd_pid} ${rsyslog_pid}

if [ "${job_id}" = ${sshd_pid} ]; then
  sshd_pid=""
  error_exit "Sshd died. Shutting down"
else
  rsyslog_pid=""
  error_exit "Rsyslog died. Shutting down"
fi


exit $?

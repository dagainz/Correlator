#!/bin/bash

# Start Correlator within Docker container

echo "Starting Correlator container"
# Create runtime structure if necessary

if [ ! -d "/var/correlator/etc" ];then
  echo "Performing first run setup"
  mkdir -p /var/correlator/etc
  mkdir -p /var/correlator/spool/csv
  cp /usr/src/app/config.json /var/correlator/etc
fi

arg=$1
shift

if [ -z "$arg" ]; then
  exec bash --init-file /usr/src/app/extra/show_banner.sh
elif [ "$arg" = "syslog_server" ]; then
  exec syslog_server "$@"
else
  echo "Error: Unknown argument: $arg"
fi


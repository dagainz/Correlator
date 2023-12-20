#!/bin/bash

# Start Correlator within Docker container


# Create runtime structure if necessary

if [ ! -d "/var/correlator/etc" ];then
  echo "** Performing first run setup"
  mkdir -p /var/correlator/etc
  mkdir -p /var/correlator/spool/csv
  cp /usr/src/app/config.json /var/correlator/etc
fi


if [ -z "$1" ]; then
  exec bash --init-file /usr/src/app/extra/show_banner.sh
elif [ "$1" = "screen" ]; then
  echo "** Screen not quite yet supported"
#  screen -Dm bash --init-file /usr/src/app/extra/show_banner.sh &
#  wait
else
  echo "** Arguments to run are not yet supported"
fi


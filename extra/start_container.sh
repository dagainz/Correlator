#!/bin/bash

# Start Correlator within Docker container


# Create runtime structure if necessary

if [ ! -d "/var/correlator/etc" ];then
  echo "** Performing first run setup"
  mkdir -p /var/correlator/etc
  mkdir -p /var/correlator/spool
  cp /usr/src/app/config.json /var/correlator/etc
fi



if [ $# -eq 0 ]; then
  exec bash --init-file /usr/src/app/extra/show_banner.sh
else
  echo "** Arguments to run are not yet supported"
fi

#if [ "$1" = "screen" ]; then
#  screen -Dm bash --init-file /usr/src/app/extra/show_banner.sh &
#  wait
#fi

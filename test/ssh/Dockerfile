FROM python:3.10-slim-bookworm

RUN apt-get update && apt-install -y rsyslog openssh-server

WORKDIR /etc/rsyslog.d

COPY correlator.conf .


CMD [ "bash" ]

# /var/spool/rsyslog - rsyslog queue

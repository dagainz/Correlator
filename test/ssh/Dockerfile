FROM python:3.10-slim-bookworm

RUN apt-get update && apt-get install -y rsyslog openssh-server
RUN sed -i '/imklog/s/^/#/' /etc/rsyslog.conf

WORKDIR /etc/rsyslog.d

COPY correlator.conf .


CMD [ "bash" ]

# /var/spool/rsyslog - rsyslog queue

FROM python:3.10-slim-bookworm

ARG USER=testguy
ARG PASS="testpass"

RUN adduser --disabled-password $USER && echo "$USER:$PASS" | chpasswd

RUN apt-get update && apt-get install -y rsyslog openssh-server
RUN sed -i '/imklog/s/^/#/' /etc/rsyslog.conf

WORKDIR /etc/rsyslog.d
COPY correlator.conf .

WORKDIR /usr/local/bin
COPY start_rsyslog_ssh.sh .
RUN chmod +x start_rsyslog_ssh.sh

CMD [ "/usr/local/bin/start_rsyslog_ssh.sh" ]


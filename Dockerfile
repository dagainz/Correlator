FROM python:3.10-slim-bookworm

ENV CORRELATOR_CFG=/var/correlator/etc/config.json

WORKDIR /usr/src/app

COPY . .

RUN pip install --upgrade pip
RUN pip install build
RUN python -m build
RUN pip install -e .

RUN pip install keyrings.cryptfile

RUN mkdir -p /var/correlator/spool
RUN mkdir -p /var/correlator/etc

RUN mv /usr/src/app/config.json /var/correlator/etc

CMD [ "bash" ]




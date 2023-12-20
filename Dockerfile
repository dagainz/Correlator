FROM python:3.10-slim-bookworm

EXPOSE 5140
ENV CORRELATOR_CFG=/var/correlator/etc/config.json
RUN apt-get update && apt-get install -y screen

WORKDIR /usr/src/app

COPY . .

RUN pip install --upgrade pip
RUN pip install build
RUN python -m build
RUN pip install .

RUN pip install keyrings.cryptfile

#RUN mkdir -p /var/correlator/spool
#RUN mkdir -p /var/correlator/etc

#RUN mv /usr/src/app/config.json /var/correlator/etc
RUN chmod +x /usr/src/app/extra/start_container.sh


# CMD [ "bash", "--init-file", "/usr/src/app/extra/show_banner.sh" ]
# CMD [ "screen", "-dm", "bash", "--init-file", "/usr/src/app/extra/show_banner.sh" ]
ENTRYPOINT [ "/usr/src/app/extra/start_container.sh" ]
CMD [ "" ]



FROM python:3.10-slim-bookworm

ARG VERSION
ARG BUILD_TYPE

RUN test -n "${VERSION}" || (echo "VERSION build argument not specified" && false)

EXPOSE 5140
ENV CORRELATOR_CFG=/var/correlator/etc/config.json
ENV CORRELATOR_VERSION=${VERSION}
ENV KEYRING_CRYPTFILE_PASSWORD=abracadabra

ENV PYCHARM_DEBUG_PORT=4200
ENV PYCHARM_DEBUG_HOST=host.docker.internal

ENV XDG_DATA_HOME=/var/correlator/etc

WORKDIR /usr/src/app

COPY . .

RUN pip install --upgrade pip
RUN pip install build
RUN python -m build
RUN if [ BUILD_TYPE=development ]; then \
      pip install -e .; \
    else \
      pip install .; \
    fi


RUN pip install keyrings.cryptfile
RUN pip install pydevd-pycharm~=233.13135.95

# Copy the startup script out of the source tree so we are able to bind mount
# the source tree to develop within this container

RUN cp /usr/src/app/extra/start_correlator_container.sh /bin
RUN chmod +x /bin/start_correlator_container.sh


ENTRYPOINT [ "/bin/start_correlator_container.sh" ]
CMD [ "" ]



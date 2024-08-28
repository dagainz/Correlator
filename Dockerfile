FROM python:3.10-slim-bookworm

ARG VERSION="0.0.4"
ARG BUILD_TYPE

# RUN test -n "${VERSION}" || (echo "VERSION build argument not specified" && false)

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

# Install package 'in-place' if this is a development build.

RUN if [ BUILD_TYPE=development ]; then \
      pip install -e .; \
    else \
      pip install .; \
    fi


# Credential handling
RUN pip install keyrings.cryptfile

# Pycharm remote debugging support
RUN pip install pydevd-pycharm~=233.13135.95

# Copy the startup script out of the application area
# This is to allow bind mounting the the correlator source into this area
# to develop, test, and debug from within the container. Also requires
# BUILD_TYPE to be development.

RUN cp /usr/src/app/extra/start_correlator_container.sh /bin
RUN chmod +x /bin/start_correlator_container.sh


ENTRYPOINT [ "/bin/start_correlator_container.sh" ]
CMD [ "" ]



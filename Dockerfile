FROM python:3.10-slim-bookworm

WORKDIR /usr/src/app

COPY . .

CMD [ "bash" ]




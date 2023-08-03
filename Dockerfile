FROM python:3.10-slim-bookworm

WORKDIR /usr/src/app

COPY . .

RUN pip install --upgrade-pip
RUN pip install build
RUN python -m build
RUN pip install -e .

CMD [ "bash" ]




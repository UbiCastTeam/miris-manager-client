FROM python:3.13-alpine

RUN apk add make

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

WORKDIR /opt/src

COPY pyproject.toml pyproject.toml
COPY mirismanagerclient mirismanagerclient
RUN pip install --no-cache-dir --editable '.[dev]'

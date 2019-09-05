FROM python:3.7-alpine

RUN apk add --no-cache make git bash
RUN apk add --no-cache gcc musl-dev python3-dev libffi-dev openssl-dev  # cryptography: https://cryptography.io/en/latest/installation/#alpine
RUN apk add --update --no-cache py3-numpy py3-scipy py3-pillow py3-zmq

#   # https://stackoverflow.com/a/57485724
ENV PYTHONPATH "$PYTHONPATH:/usr/lib/python3.7/site-packages"

RUN pip install --upgrade pip
RUN pip install protobuf colorlog graphviz # other oef dependences
RUN pip install --index-url https://test.pypi.org/simple/ oef==0.6.4  --no-deps
RUN pip install --index-url https://test.pypi.org/simple/ aea==0.1.1  --no-deps

ENTRYPOINT []

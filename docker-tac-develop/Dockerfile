FROM ubuntu:18.04

USER root

RUN apt-get update && \
    apt-get install -y dialog && \
    apt-get install -y apt-utils && \
    apt-get upgrade -y && \
    apt-get install -y sudo

# This adds the `default` user in to sudoers with full privileges:
RUN HOME=/home/default && \
    mkdir -p ${HOME} && \
    GROUP_ID=1000 && \
    USER_ID=1000 && \
    groupadd -r default -f -g "$GROUP_ID" && \
    useradd -u "$USER_ID" -r -g default -d "$HOME" -s /sbin/nologin \
    -c "Default Application User" default && \
    chown -R "$USER_ID:$GROUP_ID" ${HOME} && \
    usermod -a -G sudo default && \
    echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

RUN apt-get install -y vim && \
    apt-get install -y make && \
    apt-get install -y cmake && \
    apt-get install -y git && \
    apt-get install -y python3 && \
    apt-get install -y python-pip && \
    apt-get install -y python3-pip && \
    python -m pip install --upgrade pip && \
    python -m pip install --upgrade cldoc

RUN apt-get install -y less && \
    apt-get install -y curl && \
    apt-get install -y wget

RUN apt-get install protobuf-compiler -y &&\
    apt-get install libprotobuf-dev -y

ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/lib:/usr/lib


# install Pipenv
ENV DEBIAN_FRONTEND noninteractive
ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8

USER default

RUN sudo apt install python3.7-dev -y
RUN sudo apt install python3-pip -y
RUN sudo pip install pipenv

RUN sudo mkdir /build
WORKDIR /build
COPY . /build

RUN sudo make clean

RUN pipenv --python python3.7
RUN pipenv install --dev --skip-lock
RUN pipenv run pip3 install .

ENTRYPOINT []

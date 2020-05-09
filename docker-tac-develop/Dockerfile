FROM ubuntu:19.10

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

USER default

RUN sudo apt-get install python3.7-dev -y

RUN sudo mkdir /build
WORKDIR /build
COPY . /build

RUN sudo make clean
RUN python3.7 -m pip install -r requirements.txt
RUN python3.7 -m pip install -i https://test.pypi.org/simple/ oef==0.6.10 --no-deps
RUN python3.7 -m pip install .

ENTRYPOINT []

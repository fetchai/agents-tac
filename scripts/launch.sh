#!/usr/bin/env bash

ROOT_DIR="$( cd "$(dirname "$0")" ; pwd -P )/../";



echo "Launching the agent..."
python3 "${ROOT_DIR}"/templates/v1/basic.py "$@" &
echo "Launching the sandbox..."
cd "${ROOT_DIR}"/sandbox && docker-compose up ; cd -

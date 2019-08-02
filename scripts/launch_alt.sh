#!/usr/bin/env bash

ROOT_DIR="$( cd "$(dirname "$0")" ; pwd -P )/../";

echo "Launching the oef ..."
python3 "${ROOT_DIR}"/oef_search_pluto_scripts/launch.py -c ./oef_search_pluto_scripts/launch_config_latest.json "$@" &
echo "Launching visdom server ..."
python -m visdom.server "$@" &
echo "Sleeping for 5 seconds ..."
sleep 5
echo "Launching the spawner ..."
python "${ROOT_DIR}"/simulation/v1/tac_agent_spawner.py --gui

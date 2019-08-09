#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ------------------------------------------------------------------------------
#
#   Copyright 2018-2019 Fetch.AI Limited
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------

"""Play ground to spin up an agent and interact with it."""

import docker
import inspect
import json
import pdb
import os
import re
import subprocess
import time

from typing import Dict, Optional

from oef.messages import CFP, Message
from oef.uri import Context

from tac.agents.v1.base.dialogues import Dialogue
from tac.agents.v1.examples.baseline import BaselineAgent
from tac.agents.v1.examples.strategy import BaselineStrategy
from tac.platform.protocol import GameData

CUR_PATH = inspect.getfile(inspect.currentframe())
ROOT_DIR = os.path.join(os.path.dirname(CUR_PATH), "..")


def kill_oef():
    """Kill any running OEF instance."""
    client = docker.from_env()
    for container in client.containers.list():
        if any(re.match("fetchai/oef-search", tag) for tag in container.image.tags):
            print("Stopping existing OEF Node...")
            container.stop()


def launch_oef():
    """Launch an OEF node instance."""
    script_path = os.path.join("oef_search_pluto_scripts", "launch.py")
    configuration_file_path = os.path.join("oef_search_pluto_scripts", "launch_config_latest.json")
    print("Launching new OEF Node...")
    subprocess.Popen(["python3", script_path, "-c", configuration_file_path, "--background"],
                     stdout=subprocess.PIPE, env=os.environ, cwd=ROOT_DIR)

    # Wait for OEF
    print("Waiting for the OEF to be operative...")
    wait_for_oef = subprocess.Popen([
        os.path.join("sandbox", "wait-for-oef.sh"),
        "127.0.0.1",
        "10000",
        ":"
    ], env=os.environ, cwd=ROOT_DIR)

    wait_for_oef.wait(30)


if __name__ == '__main__':

    kill_oef()
    launch_oef()
    try:
        # Create an agent
        # Creating an agent is straightforward. You simply import the `BaselineAgent` and `BaselineStrategy` and instantiate them.
        strategy = BaselineStrategy()
        agent_one = BaselineAgent(name='agent_one', oef_addr='127.0.0.1', oef_port=10000, strategy=strategy)
        agent_two = BaselineAgent(name='agent_two', oef_addr='127.0.0.1', oef_port=10000, strategy=strategy)

        # Feed the agent some game data
        # To start, we require some game data to feed to the agent:
        money = 100.0
        initial_endowments = [2, 2, 2, 2]
        utility_params_one = [50.0, 25.0, 20.0, 5.0]
        utility_params_two = [5.0, 15.0, 30.0, 50.0]
        nb_agents = 2
        nb_goods = 4
        tx_fee = 0.01
        agent_pbk_to_name = {agent_one.crypto.public_key: agent_one.name, agent_two.crypto.public_key: agent_two.name}
        good_pbk_to_name = {'good_1_pbk': 'good_1', 'good_2_pbk': 'good_2', 'good_3_pbk': 'good_3', 'good_4_pbk': 'good_4'}

        game_data_one = GameData(agent_one.crypto.public_key,
                                 agent_one.crypto,
                                 money,
                                 initial_endowments,
                                 utility_params_one,
                                 nb_agents,
                                 nb_goods,
                                 tx_fee,
                                 agent_pbk_to_name,
                                 good_pbk_to_name)
        agent_one.game_instance.init(game_data_one, agent_one.crypto.public_key)

        game_data_two = GameData(agent_two.crypto.public_key,
                                 agent_two.crypto,
                                 money,
                                 initial_endowments,
                                 utility_params_one,
                                 nb_agents,
                                 nb_goods,
                                 tx_fee,
                                 agent_pbk_to_name,
                                 good_pbk_to_name)
        agent_two.game_instance.init(game_data_two, agent_two.crypto.public_key)

        # Set the debugger
        print("Setting debugger ... To continue enter: c + Enter")
        pdb.set_trace()

        # agent_one initiates a dialogue
        is_seller = True
        dialogue = agent_one.game_instance.dialogues.create_self_initiated(agent_two.crypto.public_key, agent_one.crypto.public_key, is_seller)  # type: Dialogue

        # agent_one creates a CFP and enqueues it in the outbox
        starting_message_id = 1
        starting_message_target = 0
        services = agent_one.game_instance.build_services_dict(is_supply=is_seller)  # type: Dict
        cfp = CFP(starting_message_id, dialogue.dialogue_label.dialogue_id, agent_two.crypto.public_key, starting_message_target, json.dumps(services).encode('utf-8'), Context())
        dialogue.outgoing_extend([cfp])
        agent_one.out_box.out_queue.put(cfp)

        # Send the messages in the outbox
        agent_one.out_box.send_nowait()

        # Check the message arrived in the inbox of agent_two
        checks = 0
        while checks < 10:
            if agent_two.in_box.is_in_queue_empty():
                # Wait a bit
                print("Sleeping for 1 second ...")
                time.sleep(1.0)
                checks += 1
            else:
                checks = 10
        msg = agent_two.in_box.get_no_wait()  # type: Optional[Message]
        print("The msg is a CFP: {}".format(isinstance(msg, CFP)))

        # Set the debugger
        print("Setting debugger ... To continue enter: c + Enter")
        pdb.set_trace()

    finally:
        kill_oef()

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
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------

"""Spawn several TAC agents."""
import argparse
import asyncio
import logging
from typing import List

from oef.query import Query, GtEq, Constraint

from tac.baseline import BaselineAgent
from tac.controller import ControllerAgent
from tac.core import TacAgent
from tac.helpers import plantuml_gen

logger = logging.getLogger("tac")


def parse_arguments():
    parser = argparse.ArgumentParser("tac_agent_spawner")
    parser.add_argument("N", type=int, help="Number of TAC agent to run.")
    parser.add_argument("--oef-addr", default="127.0.0.1", help="TCP/IP address of the OEF Agent")
    parser.add_argument("--oef-port", default=3333, help="TCP/IP port of the OEF Agent")
    parser.add_argument("--out", default="out.uml", help="The output uml file")

    arguments = parser.parse_args()
    return arguments


def run_agent(agent: BaselineAgent, loop):
    agent.connect(loop=loop)
    agent.search_tac_agents()
    agent.run(loop=loop)


def run_agents(agents: List[TacAgent]):

    from threading import Thread
    threads = [Thread(target=run_agent, args=(a, asyncio.new_event_loop())) for a in agents]
    for t in threads:
        t.start()


if __name__ == '__main__':

    try:
        arguments = parse_arguments()

        tac_controller = ControllerAgent(public_key="tac_controller", oef_addr=arguments.oef_addr,
                                         oef_port=arguments.oef_port, nb_agents=arguments.N)
        tac_controller.connect()
        tac_controller.register()

        agents = [BaselineAgent("tac_agent_" + str(i), "127.0.0.1", 3333) for i in range(arguments.N)]

        tac_agents = agents  # type: List[TacAgent]
        run_agents(tac_agents)

        tac_controller.run()
    finally:
        plantuml_gen.dump("out.uml")

    # task.add_done_callback(callback)
    # asyncio.get_event_loop().run_forever()

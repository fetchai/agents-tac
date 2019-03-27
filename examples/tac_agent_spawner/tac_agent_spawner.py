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

from oef.query import Query, GtEq, Constraint

from tac.baseline import BaselineAgent
from tac.controller import ControllerAgent
from tac.helpers import callback

logger = logging.getLogger("tac")


def parse_arguments():
    parser = argparse.ArgumentParser("tac_agent_spawner")
    parser.add_argument("N", type=int, help="Number of TAC agent to run.")

    arguments = parser.parse_args()
    return arguments


if __name__ == '__main__':

    arguments = parse_arguments()

    tac_controller = ControllerAgent(public_key="tac_controller", oef_addr="127.0.0.1", oef_port=3333,
                                     nb_agents=arguments.N)
    tac_controller.connect()
    tac_controller.register()

    agents = [BaselineAgent("tac_agent_" + str(i), "127.0.0.1", 3333) for i in range(arguments.N)]
    for a in agents:
        a.connect()
        a.search_services(0, Query([Constraint("version", GtEq(1))]))

    task = asyncio.gather(*([a.async_run() for a in agents] + [tac_controller.async_run()]))
    task.add_done_callback(callback)
    asyncio.get_event_loop().run_forever()

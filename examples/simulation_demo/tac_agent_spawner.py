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
import datetime
import logging
import pprint
from typing import List

from tac.agents.baseline import BaselineAgent
from tac.agents.controller import ControllerAgent
from tac.core import TacAgent
from tac.helpers.plantuml import plantuml_gen
from tac.stats import GameStats

logger = logging.getLogger("tac")


def parse_arguments():
    parser = argparse.ArgumentParser("tac_agent_spawner")
    parser.add_argument("--nb-agents", type=int, default=5, help="Number of TAC agent to wait for the competition.")
    parser.add_argument("--nb-goods",   type=int, default=5, help="Number of TAC agent to run.")
    parser.add_argument("--nb-baseline-agents", type=int, default=0,
                        help="Number of baseline agent to run. Defaults to the number of agents of the competition.")
    parser.add_argument("--oef-addr", default="127.0.0.1", help="TCP/IP address of the OEF Agent")
    parser.add_argument("--oef-port", default=3333, help="TCP/IP port of the OEF Agent")
    parser.add_argument("--uml-out", default=None, help="The output uml file")
    parser.add_argument("--data-output-dir", default="data", help="The output directory for the simulation data.")
    parser.add_argument("--experiment-id", default=None, help="The experiment ID.")
    parser.add_argument("--plot", default=False, type=bool, help="Plot sequence of transactions and the changes in scores.")
    parser.add_argument("--timeout", default=5, type=int, help="The amount of time (in seconds) to wait for starting the competition.")

    arguments = parser.parse_args()
    logger.debug("Arguments: {}".format(pprint.pformat(arguments.__dict__)))

    return arguments


def run_agent(agent: BaselineAgent):
    agent.connect()
    agent.search_tac_agents()
    agent.run()


def run_agents(agents: List[TacAgent]):

    from threading import Thread
    threads = [Thread(target=run_agent, args=(a, ))for a in agents]
    for t in threads:
        t.start()


arguments = parse_arguments()

if __name__ == '__main__':

    try:
        start_time = datetime.datetime.now() + datetime.timedelta(0, arguments.timeout)
        tac_controller = ControllerAgent(public_key="tac_controller", oef_addr=arguments.oef_addr,
                                         oef_port=arguments.oef_port, nb_agents=arguments.nb_agents,
                                         nb_goods=arguments.nb_goods, start_time=start_time)
        tac_controller.connect()
        tac_controller.register()

        agents = [BaselineAgent("tac_agent_" + str(i), arguments.oef_addr, arguments.oef_port,
                                loop=asyncio.new_event_loop())
                  for i in range(arguments.nb_baseline_agents)]

        tac_agents = agents  # type: List[TacAgent]
        run_agents(tac_agents)

        tac_controller.run()
    except KeyboardInterrupt:
        logger.debug("Simulation interrupted...")
    finally:
        logger.debug("Saving simulation data...")
        tac_controller.dump(arguments.data_output_dir, arguments.experiment_id)
        if arguments.uml_out is not None:
            logger.debug("Generating transition diagram...")
            plantuml_gen.dump(arguments.uml_out) if arguments.uml_out is not None else None
        if arguments.plot:
            game_stats = GameStats(tac_controller._current_game)
            game_stats.plot_score_history()


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
from threading import Thread
from typing import List

from tac.agents.baseline import BaselineAgent
from tac.agents.controller import ControllerAgent
from tac.helpers.plantuml import plantuml_gen
from tac.stats import GameStats

logger = logging.getLogger("tac")


def parse_arguments():
    parser = argparse.ArgumentParser("tac_agent_spawner")
    parser.add_argument("--nb-agents", type=int, default=10, help="(minimum) number of TAC agent to wait for the competition.")
    parser.add_argument("--nb-goods",   type=int, default=10, help="Number of TAC agent to run.")
    parser.add_argument("--nb-baseline-agents", type=int, default=10, help="Number of baseline agent to run. Defaults to the number of agents of the competition.")
    parser.add_argument("--oef-addr", default="127.0.0.1", help="TCP/IP address of the OEF Agent")
    parser.add_argument("--oef-port", default=3333, help="TCP/IP port of the OEF Agent")
    parser.add_argument("--uml", default=True, help="Plot uml file")
    parser.add_argument("--data-output-dir", default="data", help="The output directory for the simulation data.")
    parser.add_argument("--experiment-id", default=None, help="The experiment ID.")
    parser.add_argument("--plot", default=True, type=bool, help="Plot sequence of transactions and the changes in scores.")
    parser.add_argument("--lower-bound-factor", default=1, type=int, help="The lower bound factor of a uniform distribution.")
    parser.add_argument("--upper-bound-factor", default=1, type=int, help="The upper bound factor of a uniform distribution.")
    parser.add_argument("--fee", default=1, type=int, help="The transaction fee.")
    parser.add_argument("--timeout", default=5, type=int, help="The amount of time (in seconds) to wait for starting the competition.")

    arguments = parser.parse_args()
    logger.debug("Arguments: {}".format(pprint.pformat(arguments.__dict__)))

    return arguments


def _compute_competition_start_time(timeout: int) -> datetime.datetime:
    """
    Compute the start time of the competition.
    It just sums N seconds from 'now'.
    :param timeout: seconds to wait from 'now'.
    :return: the date time of the start of the competition.
    """
    delta = datetime.timedelta(0, timeout)
    now = datetime.datetime.now()

    # the start time of the competition is NOW  plus N seconds in the future, where N is in the 'timeout' variable.
    # TODO the "now" might have different meaning depending on where the following line of code is executed.
    start_time = now + delta
    return start_time


def initialize_controller_agent(public_key: str,
                                oef_addr: str,
                                oef_port: int,
                                min_nb_agents: int,
                                nb_goods: int,
                                fee: int,
                                lower_bound_factor: int,
                                upper_bound_factor: int,
                                timeout: int) -> ControllerAgent:
    """
    Initialize the controller agent.
    :param public_key: the public key of the controller agent.
    :param oef_addr: the TCP/IP address of the OEF Node.
    :param oef_port: the TCP/IP port of the OEF Node.
    :param min_nb_agents: the minimum number of agents to run the competition.
    :param nb_goods: the number of goods.
    :param fee: the transaction fee.
    :param lower_bound_factor: the lower bound factor of a uniform distribution.
    :param upper_bound_factor: the upper bound factor of a uniform distribution.
    :param timeout: the timeout (in seconds) to wait until the competition starts.
    :return: the controller agent.
    """

    start_time = _compute_competition_start_time(timeout)

    tac_controller = ControllerAgent(public_key=public_key, oef_addr=oef_addr,
                                     oef_port=oef_port, min_nb_agents=min_nb_agents,
                                     nb_goods=nb_goods, fee=fee, lower_bound_factor=lower_bound_factor,
                                     upper_bound_factor=upper_bound_factor, start_time=start_time)
    tac_controller.connect()
    tac_controller.register()
    return tac_controller


def _make_id(id: int) -> str:
    """
    Make the public key for baseline agents from an integer identifier.
    E.g. from '0' to 'tac_agent_00'.
    :param id: a numerical identifier id of the agent.
    :return: the string associated to the integer id.
    """
    return "tac_agent_{:02}".format(id)


def initialize_baseline_agent(agent_pbk: str, oef_addr: str, oef_port: int) -> BaselineAgent:
    """
    Initialize one baseline agent.
    :param agent_pbk: the public key of the Baseline agent.
    :param oef_addr: IP address of the OEF Node.
    :param oef_port: TCP port of the OEF Node.
    :return: the baseline agent.
    """

    # Notice: we create a new asyncio loop, so we can run it in an independent thread.
    return BaselineAgent(agent_pbk, oef_addr, oef_port, loop=asyncio.new_event_loop())


def initialize_baseline_agents(nb_baseline_agents: int, oef_addr: str, oef_port: int) -> List[BaselineAgent]:
    """
    Initialize a list of baseline agents.
    :param nb_baseline_agents: number of agents to initialize.
    :param oef_addr: IP address of the OEF Node.
    :param oef_port: TCP port of the OEF Node.
    :return: A list of baseline agents.
    """
    baseline_agents = [initialize_baseline_agent(_make_id(i), oef_addr, oef_port) for i in range(nb_baseline_agents)]
    return baseline_agents


def run_baseline_agent(agent: BaselineAgent) -> None:
    """Run a baseline agent."""
    agent.connect()
    agent.register_to_tac()
    agent.run()


def run_controller(tac_controller: ControllerAgent) -> None:
    """Run a controller agent."""
    tac_controller.run_controller()


def run(tac_controller: ControllerAgent, baseline_agents: List[BaselineAgent]):
    """
    Run the controller agent and all the baseline agents. More specifically:
        - run a thread for every message processing loop (i.e. the one in `oef.core.OEFProxy.loop()`).
        - start the countdown for the start of the competition.
          See the method tac.agents.controller.ControllerAgent.timeout_competition()).

    Returns only when all the jobs are completed (e.g. the timeout job) or stopped (e.g. the processing loop).
    """

    # generate task for the controller
    controller_thread = Thread(target=run_controller, args=(tac_controller, ))
    timeout_thread = Thread(target=tac_controller.game_handler.timeout_competition, args=())

    # generate tasks for baseline agents
    baseline_threads = [Thread(target=run_baseline_agent, args=(baseline_agent, ))for baseline_agent in baseline_agents]

    # launch all thread.
    all_threads = [controller_thread, timeout_thread] + baseline_threads
    for thread in all_threads:
        thread.start()

    # wait for every thread. This part is blocking.
    for thread in all_threads:
        thread.join()


if __name__ == '__main__':
    arguments = parse_arguments()
    try:

        tac_controller = initialize_controller_agent("tac_controller", arguments.oef_addr, arguments.oef_port,
                                                     arguments.nb_agents, arguments.nb_goods, arguments.fee, arguments.lower_bound_factor,
                                                     arguments.upper_bound_factor, arguments.timeout)
        baseline_agents = initialize_baseline_agents(arguments.nb_baseline_agents, arguments.oef_addr, arguments.oef_port)
        run(tac_controller, baseline_agents)

    except KeyboardInterrupt:
        logger.debug("Simulation interrupted...")
    except Exception:
        logger.exception("Unexpected exception.")
        exit(-1)
    finally:
        experiment_name = arguments.experiment_id if arguments.experiment_id is not None else str(datetime.datetime.now()).replace(" ", "_")
        logger.debug("Saving simulation data...")
        tac_controller.dump(arguments.data_output_dir, experiment_name)
        if arguments.uml:
            logger.debug("Generating transition diagram...")
            plantuml_gen.dump(arguments.data_output_dir, experiment_name)
        if arguments.plot:
            logger.debug("Plotting data...")
            game_stats = GameStats(tac_controller.game_handler.current_game)
            game_stats.dump(arguments.data_output_dir, experiment_name)

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
import datetime
import logging
import pprint
import random
from threading import Thread, Timer
from typing import List

import dateutil
import math

from tac.agents.v2.base.strategy import RegisterAs, SearchFor
from tac.agents.v2.examples.baseline import BaselineAgent
from tac.agents.v2.examples.strategy import BaselineStrategy
from tac.gui.monitor import VisdomMonitor, NullMonitor
from tac.helpers.plantuml import plantuml_gen
from tac.platform.controller import ControllerAgent, TACParameters
from tac.platform.stats import GameStats

logger = logging.getLogger("tac")


def parse_arguments():
    parser = argparse.ArgumentParser("tac_agent_spawner")
    parser.add_argument("--nb-agents", type=int, default=10, help="(minimum) number of TAC agent to wait for the competition.")
    parser.add_argument("--nb-goods", type=int, default=10, help="Number of TAC agent to run.")
    parser.add_argument("--money-endowment", type=int, default=200, help="Initial amount of money.")
    parser.add_argument("--base-good-endowment", default=2, type=int, help="The base amount of per good instances every agent receives.")
    parser.add_argument("--lower-bound-factor", default=0, type=int, help="The lower bound factor of a uniform distribution.")
    parser.add_argument("--upper-bound-factor", default=0, type=int, help="The upper bound factor of a uniform distribution.")
    parser.add_argument("--tx-fee", default=0.1, type=float, help="The transaction fee.")
    parser.add_argument("--oef-addr", default="127.0.0.1", help="TCP/IP address of the OEF Agent")
    parser.add_argument("--oef-port", default=10000, help="TCP/IP port of the OEF Agent")
    parser.add_argument("--nb-baseline-agents", type=int, default=10, help="Number of baseline agent to run. Defaults to the number of agents of the competition.")
    parser.add_argument("--start-time", default=str(datetime.datetime.now() + datetime.timedelta(0, 10)), type=str, help="The start time for the competition (in UTC format).")
    parser.add_argument("--registration-timeout", default=10, type=int, help="The amount of time (in seconds) to wait for agents to register before attempting to start the competition.")
    parser.add_argument("--inactivity-timeout", default=60, type=int, help="The amount of time (in seconds) to wait during inactivity until the termination of the competition.")
    parser.add_argument("--competition-timeout", default=240, type=int, help="The amount of time (in seconds) to wait from the start of the competition until the termination of the competition.")
    parser.add_argument("--services-interval", default=5, type=int, help="The amount of time (in seconds) the baseline agents wait until it updates services again.")
    parser.add_argument("--pending-transaction-timeout", default=120, type=int, help="The amount of time (in seconds) the baseline agents wait until the transaction confirmation.")
    parser.add_argument("--register-as", choices=['seller', 'buyer', 'both'], default='both', help="The string indicates whether the baseline agent registers as seller, buyer or both on the oef.")
    parser.add_argument("--search-for", choices=['sellers', 'buyers', 'both'], default='both', help="The string indicates whether the baseline agent searches for sellers, buyers or both on the oef.")
    parser.add_argument("--uml", default=True, help="Plot uml file")
    parser.add_argument("--data-output-dir", default="data", help="The output directory for the simulation data.")
    parser.add_argument("--experiment-id", default=None, help="The experiment ID.")
    parser.add_argument("--plot", default=True, type=bool, help="Plot sequence of transactions and the changes in scores.")
    parser.add_argument("--gui", action="store_true", help="Enable the GUI.")
    parser.add_argument("--visdom-addr", default="localhost", help="TCP/IP address of the Visdom server")
    parser.add_argument("--visdom-port", default=8097, help="TCP/IP port of the Visdom server")
    parser.add_argument("--seed", default=42, help="The random seed of the simulation.")
    parser.add_argument("--whitelist-file", nargs="?", default=None, type=str, help="The file that contains the list of agent names to be whitelisted.")

    arguments = parser.parse_args()
    logger.debug("Arguments: {}".format(pprint.pformat(arguments.__dict__)))

    return arguments


def _compute_competition_start_and_end_time(registration_timeout: int, competition_timeout: int) -> [datetime.datetime, datetime.datetime]:
    """
    Compute the start time of the competition.
    :param registration_timeout: seconds to wait for registration timeout.
    :param competition_timeout: seconds to wait for competition timeout.
    :return: list with the datetime of the start and end of the competition.
    """
    delta_now_to_start = datetime.timedelta(0, registration_timeout)
    delta_start_to_end = datetime.timedelta(0, competition_timeout)
    now = datetime.datetime.now()

    start_time = now + delta_now_to_start
    end_time = start_time + delta_start_to_end
    return start_time, end_time


def initialize_controller_agent(name: str,
                                oef_addr: str,
                                oef_port: int,
                                visdom_addr: str,
                                visdom_port: int,
                                gui: bool) -> ControllerAgent:
    """
    Initialize the controller agent.
    :param name: the name of the controller agent.
    :param oef_addr: the TCP/IP address of the OEF Node.
    :param oef_port: the TCP/IP port of the OEF Node.
    :param visdom_addr: TCP/IP address of the Visdom server.
    :param visdom_port: TCP/IP port of the Visdom server.
    :return: the controller agent.
    """

    monitor = VisdomMonitor(visdom_addr=visdom_addr, visdom_port=visdom_port) if gui else NullMonitor()
    tac_controller = ControllerAgent(name=name, oef_addr=oef_addr, oef_port=oef_port, monitor=monitor)

    tac_controller.connect()
    tac_controller.register()
    return tac_controller


def _make_id(agent_id: int, is_world_modeling: bool, nb_agents: int) -> str:
    """
    Make the name for baseline agents from an integer identifier.
    E.g. from '0' to 'tac_agent_00'.

    E.g.:

    >>> _make_id(2, 10)
    'agent_2'
    >>> _make_id(2, 100)
    'agent_02'
    >>> _make_id(2, 101)
    'agent_002'

    :param agent_id: the agent id.
    :param is_world_modeling: the boolean indicated whether the baseline agent models the world around her or not.
    :param nb_agents: the overall number of agents.
    :return: the formatted name.
    :return: the string associated to the integer id.
    """
    max_number_of_digits = math.ceil(math.log10(nb_agents))
    if is_world_modeling:
        string_format = "tac_agent_{:0" + str(max_number_of_digits) + "}_wm"
    else:
        string_format = "tac_agent_{:0" + str(max_number_of_digits) + "}"
    result = string_format.format(agent_id)
    return result


def initialize_baseline_agent(agent_name: str, oef_addr: str, oef_port: int, register_as: str, search_for: str, is_world_modeling: bool, services_interval: int, pending_transaction_timeout: int) -> BaselineAgent:
    """
    Initialize one baseline agent.
    :param agent_name: the name of the Baseline agent.
    :param oef_addr: IP address of the OEF Node.
    :param oef_port: TCP port of the OEF Node.
    :param register_as: the string indicates whether the baseline agent registers as seller, buyer or both on the oef.
    :param search_for: the string indicates whether the baseline agent searches for sellers, buyers or both on the oef.
    :param is_world_modeling: the boolean indicated whether the baseline agent models the world around her or not.
    :param pending_transaction_timeout: seconds that baseline agents wait for transaction confirmations.

    :return: the baseline agent.
    """

    # Notice: we create a new asyncio loop, so we can run it in an independent thread.
    strategy = BaselineStrategy(register_as=RegisterAs(register_as), search_for=SearchFor(search_for), is_world_modeling=is_world_modeling)
    return BaselineAgent(agent_name, oef_addr, oef_port, strategy, services_interval=services_interval, pending_transaction_timeout=pending_transaction_timeout)


def initialize_baseline_agents(nb_baseline_agents: int, oef_addr: str, oef_port: int, register_as: str, search_for: str, services_interval: int, pending_transaction_timeout: int) -> List[BaselineAgent]:
    """
    Initialize a list of baseline agents.
    :param nb_baseline_agents: number of agents to initialize.
    :param oef_addr: IP address of the OEF Node.
    :param oef_port: TCP port of the OEF Node.
    :param register_as: the string indicates whether the baseline agent registers as seller, buyer or both on the oef.
    :param search_for: the string indicates whether the baseline agent searches for sellers, buyers or both on the oef.
    :param pending_transaction_timeout: seconds that baseline agents wait for transaction confirmations.

    :return: A list of baseline agents.
    """
    fraction_world_modeling = 0.1
    nb_baseline_agents_world_modeling = round(nb_baseline_agents * fraction_world_modeling)
    baseline_agents = [initialize_baseline_agent(_make_id(i, i < nb_baseline_agents_world_modeling, nb_baseline_agents), oef_addr, oef_port, register_as, search_for, i < nb_baseline_agents_world_modeling, services_interval, pending_transaction_timeout)
                       for i in range(nb_baseline_agents)]
    return baseline_agents


def run_baseline_agent(agent: BaselineAgent) -> None:
    """Run a baseline agent."""
    agent.start()


def run_controller(tac_controller: ControllerAgent, tac_parameters: TACParameters) -> None:
    """Run a controller agent."""
    tac_controller.wait_and_start_competition(tac_parameters)


def run_simulation(tac_controller: ControllerAgent, tac_parameters: TACParameters, baseline_agents: List[BaselineAgent]):
    """
    Run the controller agent and all the baseline agents. More specifically:
        - run a thread for every message processing loop (i.e. the one in `oef.core.OEFProxy.loop()`).
        - start the countdown for the start of the competition.
          See the method tac.agents.controller.ControllerAgent.timeout_competition()).

    Returns only when all the jobs are completed (e.g. the timeout job) or stopped (e.g. the processing loop).
    """

    # generate task for the controller
    controller_thread = Thread(target=run_controller, args=(tac_controller, tac_parameters))

    # generate tasks for baseline agents
    total_seconds_to_wait = (tac_parameters.start_time - datetime.datetime.now()).total_seconds()
    waiting_interval = max(1.0, total_seconds_to_wait)
    baseline_threads = [Timer(interval=waiting_interval, function=run_baseline_agent, args=[baseline_agent]) for baseline_agent in baseline_agents]

    # launch all thread.
    all_threads = [controller_thread] + baseline_threads
    for thread in all_threads:
        thread.start()

    # wait for every thread. This part is blocking.
    for thread in all_threads:
        thread.join()


def initialize_tac_parameters(arguments: argparse.Namespace) -> TACParameters:
    """
    Initialize a TACParameters object.
    :param arguments: the argparse namespace
    :return: a TACParameters object
    """
    whitelist = set(open(arguments.whitelist_file).read().splitlines(keepends=False)) if arguments.whitelist_file else None
    start_datetime = dateutil.parser.parse(arguments.start_time)
    tac_parameters = TACParameters(min_nb_agents=arguments.nb_agents,
                                   money_endowment=arguments.money_endowment,
                                   nb_goods=arguments.nb_goods,
                                   tx_fee=arguments.tx_fee,
                                   base_good_endowment=arguments.base_good_endowment,
                                   lower_bound_factor=arguments.lower_bound_factor,
                                   upper_bound_factor=arguments.upper_bound_factor,
                                   start_time=start_datetime,
                                   registration_timeout=arguments.registration_timeout,
                                   competition_timeout=arguments.competition_timeout,
                                   inactivity_timeout=arguments.inactivity_timeout,
                                   whitelist=whitelist)

    return tac_parameters


def _handling_end_of_simulation(tac_controller: 'ControllerAgent', arguments: argparse.Namespace) -> None:
    """
    Handle the end of the simulation. In particular, If the controller has been initialized:
    - save the simulation data
    - generate transition diagram, if enabled
    - plot data, if requested

    :param tac_controller: the controller agent of TAC.
    :return: None
    """
    if tac_controller is not None and tac_controller.game_handler is not None:
        tac_controller.terminate()
        logger.debug("Saving simulation data...")
        experiment_name = arguments.experiment_id if arguments.experiment_id is not None else str(
            datetime.datetime.now()).replace(" ", "_")
        tac_controller.dump(arguments.data_output_dir, experiment_name)
        if arguments.uml:
            logger.debug("Generating transition diagram...")
            plantuml_gen.dump(arguments.data_output_dir, experiment_name)
        if arguments.plot and tac_controller.game_handler.is_game_running():
            logger.debug("Plotting data...")
            game_stats = GameStats(tac_controller.game_handler.current_game)
            game_stats.dump(arguments.data_output_dir, experiment_name)


if __name__ == '__main__':
    arguments = parse_arguments()
    random.seed(arguments.seed)
    tac_controller = None
    try:

        tac_controller = initialize_controller_agent("tac_controller",
                                                     oef_addr=arguments.oef_addr,
                                                     oef_port=arguments.oef_port,
                                                     visdom_addr=arguments.visdom_addr,
                                                     visdom_port=arguments.visdom_port,
                                                     gui=arguments.gui)

        baseline_agents = initialize_baseline_agents(nb_baseline_agents=arguments.nb_baseline_agents,
                                                     oef_addr=arguments.oef_addr,
                                                     oef_port=arguments.oef_port,
                                                     register_as=arguments.register_as,
                                                     search_for=arguments.search_for,
                                                     services_interval=arguments.services_interval,
                                                     pending_transaction_timeout=arguments.pending_transaction_timeout)

        tac_parameters = initialize_tac_parameters(arguments)

        run_simulation(tac_controller, tac_parameters, baseline_agents)

    except KeyboardInterrupt:
        logger.debug("Simulation interrupted...")
    except Exception:
        logger.exception("Unexpected exception.")
        exit(-1)
    finally:
        _handling_end_of_simulation(tac_controller, arguments)

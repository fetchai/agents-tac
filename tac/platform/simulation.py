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

"""
This module implements a TAC simulation.

It spawn a controller agent that handles the competition and
several baseline agents that will participate to the competition.

It requires an OEF node running and a Visdom server, if the visualization is desired.

You can also run it as a script. To check the available arguments:

    python -m tac.platform.simulation -h

"""

import argparse
import datetime
import logging
import multiprocessing
import pprint
import random
import time
from typing import Optional, List

import dateutil

from tac.agents.controller.agent import main as controller_main
from tac.agents.controller.base.tac_parameters import TACParameters
from tac.agents.participant.v1.base.strategy import RegisterAs, SearchFor
from tac.agents.participant.v1.examples.baseline import main as baseline_main
from tac.platform.game.helpers import make_agent_name

logger = logging.getLogger(__name__)


class SimulationParams:
    """Class to hold simulation parameters."""

    def __init__(self,
                 oef_addr: str = "localhost",
                 oef_port: int = 10000,
                 nb_baseline_agents: int = 5,
                 register_as: RegisterAs = RegisterAs.BOTH,
                 search_for: SearchFor = SearchFor.BOTH,
                 services_interval: int = 5,
                 pending_transaction_timeout: int = 120,
                 verbose: bool = False,
                 dashboard: bool = False,
                 visdom_addr: str = "localhost",
                 visdom_port: int = 8097,
                 data_output_dir: Optional[str] = "data",
                 version_id: str = str(random.randint(0, 10000)),
                 seed: int = 42,
                 nb_baseline_agents_world_modeling: int = 1,
                 tac_parameters: Optional[TACParameters] = None):
        """
        Initialize a SimulationParams class.

        :param oef_addr: the IP address of the OEF.
        :param oef_port: the port of the OEF.
        :param nb_baseline_agents: the number of baseline agents to spawn.
        :param register_as: the registration policy the agents will follow.
        :param search_for: the search policy the agents will follow.
        :param services_interval: The amount of time (in seconds) the baseline agents wait until it updates services again.
        :param pending_transaction_timeout: The amount of time (in seconds) the baseline agents wait until the transaction confirmation.
        :param verbose: control the verbosity of the simulation.
        :param dashboard: enable the Visdom visualization.
        :param visdom_addr: the IP address of the Visdom server
        :param visdom_port: the port of the Visdom server.
        :param data_output_dir: the path to the output directory.
        :param version_id: the name of the experiment.
        :param seed: the random seed.
        :param nb_baseline_agents_world_modeling: the number of world modelling baseline agents.
        :param tac_parameters: the parameters for the TAC.
        """
        self.tac_parameters = tac_parameters if tac_parameters is not None else TACParameters()
        self.oef_addr = oef_addr
        self.oef_port = oef_port
        self.nb_baseline_agents = nb_baseline_agents
        self.register_as = register_as
        self.search_for = search_for
        self.services_interval = services_interval
        self.pending_transaction_timeout = pending_transaction_timeout
        self.verbose = verbose
        self.dashboard = dashboard
        self.visdom_addr = visdom_addr
        self.visdom_port = visdom_port
        self.data_output_dir = data_output_dir
        self.version_id = version_id
        self.seed = seed
        self.nb_baseline_agents_world_modeling = nb_baseline_agents_world_modeling


def spawn_controller_agent(params: SimulationParams) -> multiprocessing.Process:
    """
    Spawn a controller agent.

    :param params: the simulation params.
    :return: the process running the controller.
    """
    process = multiprocessing.Process(target=controller_main, kwargs=dict(
        name="tac_controller",
        nb_agents=params.tac_parameters.min_nb_agents,
        nb_goods=params.tac_parameters.nb_goods,
        money_endowment=params.tac_parameters.money_endowment,
        base_good_endowment=params.tac_parameters.base_good_endowment,
        lower_bound_factor=params.tac_parameters.lower_bound_factor,
        upper_bound_factor=params.tac_parameters.upper_bound_factor,
        tx_fee=params.tac_parameters.tx_fee,
        oef_addr=params.oef_addr,
        oef_port=params.oef_port,
        start_time=params.tac_parameters.start_time,
        registration_timeout=params.tac_parameters.registration_timeout,
        inactivity_timeout=params.tac_parameters.inactivity_timeout,
        competition_timeout=params.tac_parameters.competition_timeout,
        whitelist_file=params.tac_parameters.whitelist,
        verbose=True,
        dashboard=params.dashboard,
        visdom_addr=params.visdom_addr,
        visdom_port=params.visdom_port,
        data_output_dir=params.data_output_dir,
        version_id=params.version_id,
        seed=params.seed,
    ))
    process.start()
    return process


def spawn_baseline_agents(params: SimulationParams) -> List[multiprocessing.Process]:
    """
    Spawn baseline agents.

    :param params: the simulation params.
    :return: the processes running the agents (as a list).
    """
    processes = [multiprocessing.Process(target=baseline_main, kwargs=dict(
        name=make_agent_name(i, i < params.nb_baseline_agents_world_modeling, params.nb_baseline_agents),
        oef_addr=params.oef_addr,
        oef_port=params.oef_port,
        register_as=params.register_as,
        search_for=params.search_for,
        is_world_modeling=i < params.nb_baseline_agents_world_modeling,
        services_interval=params.services_interval,
        pending_transaction_timeout=params.pending_transaction_timeout,
        dashboard=params.dashboard,
        visdom_addr=params.visdom_addr,
        visdom_port=params.visdom_port)) for i in range(params.nb_baseline_agents)]

    for process in processes:
        process.start()

    return processes


def parse_arguments():
    """Arguments parsing."""
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
    parser.add_argument("--registration-timeout", default=20, type=int, help="The amount of time (in seconds) to wait for agents to register before attempting to start the competition.")
    parser.add_argument("--inactivity-timeout", default=60, type=int, help="The amount of time (in seconds) to wait during inactivity until the termination of the competition.")
    parser.add_argument("--competition-timeout", default=240, type=int, help="The amount of time (in seconds) to wait from the start of the competition until the termination of the competition.")
    parser.add_argument("--services-interval", default=5, type=int, help="The amount of time (in seconds) the baseline agents wait until it updates services again.")
    parser.add_argument("--pending-transaction-timeout", default=120, type=int, help="The amount of time (in seconds) the baseline agents wait until the transaction confirmation.")
    parser.add_argument("--register-as", choices=['seller', 'buyer', 'both'], default='both', help="The string indicates whether the baseline agent registers as seller, buyer or both on the oef.")
    parser.add_argument("--search-for", choices=['sellers', 'buyers', 'both'], default='both', help="The string indicates whether the baseline agent searches for sellers, buyers or both on the oef.")
    parser.add_argument("--dashboard", action="store_true", help="Enable the agent dashboard.")
    parser.add_argument("--data-output-dir", default="data", help="The output directory for the simulation data.")
    parser.add_argument("--version-id", default=str(random.randint(0, 10000)), type=str, help="The version ID.")
    parser.add_argument("--visdom-addr", default="localhost", help="TCP/IP address of the Visdom server")
    parser.add_argument("--visdom-port", default=8097, help="TCP/IP port of the Visdom server")
    parser.add_argument("--seed", default=42, help="The random seed of the simulation.")
    parser.add_argument("--fraction-world-modeling", default=0.1, type=float, choices=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0], help="The fraction of world modelling baseline agents.")
    parser.add_argument("--whitelist-file", nargs="?", default=None, type=str, help="The file that contains the list of agent names to be whitelisted.")

    arguments = parser.parse_args()
    logger.debug("Arguments: {}".format(pprint.pformat(arguments.__dict__)))

    return arguments


def build_simulation_parameters(arguments: argparse.Namespace) -> SimulationParams:
    """
    From argparse output, build an instance of SimulationParams.

    :param arguments: the arguments
    :return: the simulation parameters
    """
    tac_parameters = TACParameters(
        min_nb_agents=arguments.nb_agents,
        money_endowment=arguments.money_endowment,
        nb_goods=arguments.nb_goods,
        tx_fee=arguments.tx_fee,
        base_good_endowment=arguments.base_good_endowment,
        lower_bound_factor=arguments.lower_bound_factor,
        upper_bound_factor=arguments.upper_bound_factor,
        start_time=dateutil.parser.parse(arguments.start_time),
        registration_timeout=arguments.registration_timeout,
        competition_timeout=arguments.competition_timeout,
        inactivity_timeout=arguments.inactivity_timeout,
        whitelist=arguments.whitelist_file,
        data_output_dir=arguments.data_output_dir,
        version_id=arguments.version_id
    )

    simulation_params = SimulationParams(
        oef_addr=arguments.oef_addr,
        oef_port=arguments.oef_port,
        nb_baseline_agents=arguments.nb_baseline_agents,
        dashboard=arguments.dashboard,
        visdom_addr=arguments.visdom_addr,
        visdom_port=arguments.visdom_port,
        data_output_dir=arguments.data_output_dir,
        version_id=arguments.version_id,
        seed=arguments.seed,
        nb_baseline_agents_world_modeling=round(arguments.nb_baseline_agents * arguments.fraction_world_modeling),
        tac_parameters=tac_parameters
    )

    return simulation_params


def run(params: SimulationParams) -> None:
    """
    Run the simulation.

    :param params: the simulation parameters
    :return: None
    """
    random.seed(params.seed)

    controller_process = None  # type: Optional[multiprocessing.Process]
    baseline_processes = []  # type: List[multiprocessing.Process]

    try:

        controller_process = spawn_controller_agent(params)
        # give the time to the controller to connect to the OEF
        time.sleep(5.0)
        baseline_processes = spawn_baseline_agents(params)
        controller_process.join()

    except KeyboardInterrupt:
        logger.debug("Simulation interrupted...")
    except Exception:
        logger.exception("Unexpected exception.")
        exit(-1)
    finally:
        if controller_process is not None:
            controller_process.join(timeout=5)
            controller_process.terminate()

        for process in baseline_processes:
            process.join(timeout=5)
            process.terminate()


if __name__ == '__main__':
    arguments = parse_arguments()
    simulation_parameters = build_simulation_parameters(arguments)
    run(simulation_parameters)

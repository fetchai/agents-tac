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
import math
import multiprocessing
import pprint
import random
import signal
import time
from typing import Optional, List

import tac
from tac.agents.v2.examples.baseline import BaselineAgent
from tac.platform.controller import ControllerAgent

logger = logging.getLogger("tac")


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
    parser.add_argument("--registration-timeout", default=10, type=int, help="The amount of time (in seconds) to wait for agents to register before attempting to start the competition.")
    parser.add_argument("--inactivity-timeout", default=60, type=int, help="The amount of time (in seconds) to wait during inactivity until the termination of the competition.")
    parser.add_argument("--competition-timeout", default=240, type=int, help="The amount of time (in seconds) to wait from the start of the competition until the termination of the competition.")
    parser.add_argument("--services-interval", default=5, type=int, help="The amount of time (in seconds) the baseline agents wait until it updates services again.")
    parser.add_argument("--pending-transaction-timeout", default=120, type=int, help="The amount of time (in seconds) the baseline agents wait until the transaction confirmation.")
    parser.add_argument("--register-as", choices=['seller', 'buyer', 'both'], default='both', help="The string indicates whether the baseline agent registers as seller, buyer or both on the oef.")
    parser.add_argument("--search-for", choices=['sellers', 'buyers', 'both'], default='both', help="The string indicates whether the baseline agent searches for sellers, buyers or both on the oef.")
    parser.add_argument("--gui", action="store_true", help="Enable the GUI.")
    parser.add_argument("--data-output-dir", default="data", help="The output directory for the simulation data.")
    parser.add_argument("--experiment-id", default=None, help="The experiment ID.")
    parser.add_argument("--visdom-addr", default="localhost", help="TCP/IP address of the Visdom server")
    parser.add_argument("--visdom-port", default=8097, help="TCP/IP port of the Visdom server")
    parser.add_argument("--seed", default=42, help="The random seed of the simulation.")
    parser.add_argument("--whitelist-file", nargs="?", default=None, type=str, help="The file that contains the list of agent names to be whitelisted.")

    arguments = parser.parse_args()
    logger.debug("Arguments: {}".format(pprint.pformat(arguments.__dict__)))

    return arguments


def _make_id(agent_id: int, is_world_modeling: bool, nb_agents: int) -> str:
    """
    Make the name for baseline agents from an integer identifier.

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


def spawn_controller_agent(arguments):
    result = multiprocessing.Process(target=tac.platform.controller.main, kwargs=dict(
            name="tac_controller",
            nb_agents=arguments.nb_agents,
            nb_goods=arguments.nb_goods,
            money_endowment=arguments.money_endowment,
            base_good_endowment=arguments.base_good_endowment,
            lower_bound_factor=arguments.lower_bound_factor,
            upper_bound_factor=arguments.upper_bound_factor,
            tx_fee=arguments.tx_fee,
            oef_addr=arguments.oef_addr,
            oef_port=arguments.oef_port,
            start_time=arguments.start_time,
            registration_timeout=arguments.registration_timeout,
            inactivity_timeout=arguments.inactivity_timeout,
            competition_timeout=arguments.competition_timeout,
            whitelist_file=arguments.whitelist_file,
            verbose=True,
            gui=arguments.gui,
            visdom_addr=arguments.visdom_addr,
            visdom_port=arguments.visdom_port,
            data_output_dir=arguments.data_output_dir,
            experiment_id=arguments.experiment_id,
            seed=arguments.seed,
            version=1,
        ))
    result.start()
    return result


def run_baseline_agent(**kwargs) -> None:
    """
    Run a baseline agent.
    """
    # give the time to the controller to connect to the OEF
    time.sleep(5.0)
    tac.agents.v2.examples.baseline.main(**kwargs)


def spawn_baseline_agents(arguments) -> List[multiprocessing.Process]:
    fraction_world_modeling = 0.1
    nb_baseline_agents_world_modeling = round(arguments.nb_baseline_agents * fraction_world_modeling)

    threads = [multiprocessing.Process(target=run_baseline_agent, kwargs=dict(
            name=_make_id(i, i < nb_baseline_agents_world_modeling, arguments.nb_agents),
            oef_addr=arguments.oef_addr,
            oef_port=arguments.oef_port,
            register_as=arguments.register_as,
            search_for=arguments.search_for,
            is_world_modeling=i < nb_baseline_agents_world_modeling,
            services_interval=arguments.services_interval,
            pending_transaction_timeout=arguments.pending_transaction_timeout,
            gui=arguments.gui,
            visdom_addr=arguments.visdom_addr,
            visdom_port=arguments.visdom_port)) for i in range(arguments.nb_agents)]

    def signal_handler(sig, frame):
        """This is a signal handler that does nothing - used to filter the SIGINT from the parent process."""

    original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGINT, signal_handler)
    for t in threads:
        t.start()
    signal.signal(signal.SIGINT, original_sigint_handler)
    return threads


if __name__ == '__main__':
    arguments = parse_arguments()
    random.seed(arguments.seed)

    controller_thread = None  # type: Optional[multiprocessing.Process]
    baseline_threads = []  # type: List[multiprocessing.Process]

    try:

        controller_thread = spawn_controller_agent(arguments)
        baseline_threads = spawn_baseline_agents(arguments)
        controller_thread.join()

    except KeyboardInterrupt:
        logger.debug("Simulation interrupted...")
    except Exception:
        logger.exception("Unexpected exception.")
        exit(-1)
    finally:
        if controller_thread is not None:
            controller_thread.join(timeout=5)
            controller_thread.terminate()

        for t in baseline_threads:
            t.join(timeout=5)
            t.terminate()

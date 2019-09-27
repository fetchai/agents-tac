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

"""This module contains the ControllerAgent."""
import os;
import argparse
import datetime
import logging
import pprint
import random
import time
from typing import Optional

import dateutil.parser
from aea.agent import Agent
from aea.channels.oef.connection import OEFMailBox
from aea.mail.base import Envelope

from tac.agents.controller.base.handlers import OEFHandler, GameHandler, AgentMessageDispatcher
from tac.agents.controller.base.tac_parameters import TACParameters
from tac.platform.game.base import GamePhase
from tac.gui.monitor import Monitor, NullMonitor, VisdomMonitor

from tac.platform.shared_sim_status import set_controller_state, ControllerAgentState

if __name__ != "__main__":
    logger = logging.getLogger(__name__)
else:
    logger = logging.getLogger("tac.platform.controller")


class ControllerAgent(Agent):
    """The controller agent class implements a controller for TAC."""

    def __init__(self, name: str,
                 oef_addr: str,
                 oef_port: int,
                 tac_parameters: TACParameters,
                 monitor: Monitor,
                 agent_timeout: Optional[float] = 1.0,
                 max_reactions: int = 100,
                 private_key_pem: Optional[str] = None,
                 debug: bool = False,
                 **kwargs):
        """
        Initialize a participant agent.

        :param name: the name of the agent.
        :param oef_addr: the TCP/IP address of the OEF node.
        :param oef_port: the TCP/IP port of the OEF node.
        :param strategy: the strategy object that specify the behaviour during the competition.
        :param agent_timeout: the time in (fractions of) seconds to time out an agent between act and react.
        :param max_reactions: the maximum number of reactions (messages processed) per call to react.
        :param monitor: a Visdom dashboard to visualize agent statistics during the competition.
        :param private_key_pem: the path to a private key in PEM format.
        :param debug: if True, run the agent in debug mode.
        """
        super().__init__(name, private_key_pem, agent_timeout, debug=debug)
        self.mailbox = OEFMailBox(self.crypto.public_key, oef_addr, oef_port)

        self.oef_handler = OEFHandler(self.crypto, self.liveness, self.mailbox, self.name, tac_parameters.version_id)
        self.agent_message_dispatcher = AgentMessageDispatcher(self)
        self.game_handler = GameHandler(name, self.crypto, self.mailbox, monitor, tac_parameters)

        self.max_reactions = max_reactions
        self.last_activity = datetime.datetime.now()

        logger.debug("[{}]: Initialized myself as Controller Agent :\n{}".format(self.name, pprint.pformat(vars())))
        set_controller_state(self.game_handler.tac_parameters.version_id, ControllerAgentState.STARTING)



    def act(self) -> None:
        """
        Perform the agent's actions.

        :return: None
        """
        if self.game_handler.game_phase == GamePhase.PRE_GAME:
            now = datetime.datetime.now()
            seconds_to_wait = (self.game_handler.tac_parameters.start_time - now).total_seconds()
            seconds_to_wait = 0.5 if seconds_to_wait < 0 else seconds_to_wait
            logger.debug("[{}]: waiting for starting the competition: start_time={}, current_time={}, timedelta ={}s"
                         .format(self.name, str(self.game_handler.tac_parameters.start_time), str(now), seconds_to_wait))
            self.game_handler.competition_start = now + datetime.timedelta(seconds=seconds_to_wait + self.game_handler.tac_parameters.registration_timedelta.seconds)

            time.sleep(seconds_to_wait)
            logger.debug("[{}]: Register competition with parameters: {}"
                         .format(self.name, pprint.pformat(self.game_handler.tac_parameters.__dict__)))
            self.oef_handler.register_tac()

            set_controller_state(self.game_handler.tac_parameters.version_id, ControllerAgentState.REGISTRATION_OPEN)



            self.game_handler._game_phase = GamePhase.GAME_SETUP
        elif self.game_handler.game_phase == GamePhase.GAME_SETUP:
            assert self.game_handler.competition_start is not None, "No competition start time set!"
            now = datetime.datetime.now()
            if now >= self.game_handler.competition_start:
                logger.debug("[{}]: Checking if we can start the competition.".format(self.name))
                min_nb_agents = self.game_handler.tac_parameters.min_nb_agents
                nb_reg_agents = len(self.game_handler.registered_agents)

                # Remove temporary file (temporary measure to communicate)
                set_controller_state(self.game_handler.tac_parameters.version_id, ControllerAgentState.RUNNING)

                if nb_reg_agents >= min_nb_agents:
                    logger.debug("[{}]: Start competition. Registered agents: {}, minimum number of agents: {}."
                                 .format(self.name, nb_reg_agents, min_nb_agents))
                    self.game_handler.start_competition()
                else:
                    logger.debug("[{}]: Not enough agents to start TAC. Registered agents: {}, minimum number of agents: {}."
                                 .format(self.name, nb_reg_agents, min_nb_agents))
                    set_controller_state(self.game_handler.tac_parameters.version_id, ControllerAgentState.STOPPING_UNSUFFICIENT_AGENTS)
                    self.stop()
                    return
        elif self.game_handler.game_phase == GamePhase.GAME:
            current_time = datetime.datetime.now()
            inactivity_duration = current_time - self.last_activity
            if inactivity_duration > self.game_handler.tac_parameters.inactivity_timedelta:
                logger.debug("[{}]: Inactivity timeout expired. Terminating...".format(self.name))
                set_controller_state(self.game_handler.tac_parameters.version_id, ControllerAgentState.FINISHED_INACTIVITY)
                self.stop()
                return
            elif current_time > self.game_handler.tac_parameters.end_time:
                logger.debug("[{}]: Competition timeout expired. Terminating...".format(self.name))
                set_controller_state(self.game_handler.tac_parameters.version_id, ControllerAgentState.FINISHED_GAME_TIMEOUT)
                self.stop()
                return

    def react(self) -> None:
        """
        React to incoming events.

        :return: None
        """
        counter = 0
        while (not self.inbox.empty() and counter < self.max_reactions):
            counter += 1
            envelope = self.inbox.get_nowait()  # type: Optional[Envelope]
            if envelope is not None:
                if envelope.protocol_id == 'oef':
                    self.oef_handler.handle_oef_message(envelope)
                elif envelope.protocol_id == 'tac':
                    self.agent_message_dispatcher.handle_agent_message(envelope)
                    self.last_activity = datetime.datetime.now()
                else:
                    raise ValueError("Unknown protocol_id: {}".format(envelope.protocol_id))

    def update(self) -> None:
        """
        Update the state of the agent.

        :return: None
        """

    def setup(self) -> None:
        """Set up the agent."""

    def start(self) -> None:
        """
        Start the agent.

        :return: None
        """
        try:
            super().start()
            logger.debug("[{}]: Starting myself...".format(self.name))
            return
        except Exception as e:
            logger.exception(e)
            logger.debug("[{}]: Stopping myself...".format(self.name))
            self.stop()

        # here only if an error occurred
        logger.debug("[{}]: Trying to rejoin in 2 seconds...".format(self.name))
        time.sleep(2.0)
        self.start()

    def stop(self) -> None:
        """
        Stop the agent.

        :return: None
        """
        logger.debug("[{}]: Stopping myself...".format(self.name))
        if self.game_handler.game_phase == GamePhase.GAME or self.game_handler.game_phase == GamePhase.GAME_SETUP:
            self.game_handler.notify_competition_cancelled()
        super().stop()
        self.teardown()

    def teardown(self) -> None:
        """Tear down the agent."""
        if self.game_handler.monitor.is_running:
            self.game_handler.monitor.stop()
        self.game_handler.simulation_dump()


def _parse_arguments():
    parser = argparse.ArgumentParser("controller", description="Launch the controller agent.")
    parser.add_argument("--name", default="controller", help="Name of the agent.")
    parser.add_argument("--nb-agents", default=5, type=int, help="Number of goods")
    parser.add_argument("--nb-goods", default=5, type=int, help="Number of goods")
    parser.add_argument("--money-endowment", type=int, default=200, help="Initial amount of money.")
    parser.add_argument("--base-good-endowment", default=2, type=int, help="The base amount of per good instances every agent receives.")
    parser.add_argument("--lower-bound-factor", default=0, type=int, help="The lower bound factor of a uniform distribution.")
    parser.add_argument("--upper-bound-factor", default=0, type=int, help="The upper bound factor of a uniform distribution.")
    parser.add_argument("--tx-fee", default=1.0, type=float, help="Number of goods")
    parser.add_argument("--oef-addr", default="127.0.0.1", help="TCP/IP address of the OEF Agent")
    parser.add_argument("--oef-port", default=10000, help="TCP/IP port of the OEF Agent")
    parser.add_argument("--start-time", default=str(datetime.datetime.now() + datetime.timedelta(0, 10)), type=str, help="The start time for the competition (in UTC format).")
    parser.add_argument("--registration-timeout", default=20, type=int, help="The amount of time (in seconds) to wait for agents to register before attempting to start the competition.")
    parser.add_argument("--inactivity-timeout", default=60, type=int, help="The amount of time (in seconds) to wait during inactivity until the termination of the competition.")
    parser.add_argument("--competition-timeout", default=240, type=int, help="The amount of time (in seconds) to wait from the start of the competition until the termination of the competition.")
    parser.add_argument("--whitelist-file", default=None, type=str, help="The file that contains the list of agent names to be whitelisted.")
    parser.add_argument("--verbose", default=False, action="store_true", help="Log debug messages.")
    parser.add_argument("--dashboard", action="store_true", help="Show the agent dashboard.")
    parser.add_argument("--visdom-addr", default="localhost", help="TCP/IP address of the Visdom server.")
    parser.add_argument("--visdom-port", default=8097, help="TCP/IP port of the Visdom server.")
    parser.add_argument("--data-output-dir", default="data", help="The output directory for the simulation data.")
    parser.add_argument("--version-id", default=str(random.randint(0, 10000)), type=str, help="The version ID.")
    parser.add_argument("--seed", default=42, help="The random seed for the generation of the game parameters.")

    return parser.parse_args()


def main(
        name: str = "controller",
        nb_agents: int = 5,
        nb_goods: int = 5,
        money_endowment: int = 200,
        base_good_endowment: int = 2,
        lower_bound_factor: int = 0,
        upper_bound_factor: int = 0,
        tx_fee: float = 1.0,
        oef_addr: str = "127.0.0.1",
        oef_port: int = 10000,
        start_time: str = str(datetime.datetime.now() + datetime.timedelta(0, 10)),
        registration_timeout: int = 10,
        inactivity_timeout: int = 60,
        competition_timeout: int = 240,
        whitelist_file: Optional[str] = None,
        verbose: bool = False,
        dashboard: bool = False,
        visdom_addr: str = "localhost",
        visdom_port: int = 8097,
        data_output_dir: str = "data",
        version_id: str = str(random.randint(0, 10000)),
        seed: int = 42,
        **kwargs
):
    """Run the controller script."""
    agent = None  # type: Optional[ControllerAgent]
    random.seed(seed)

    if verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    try:
        monitor = VisdomMonitor(visdom_addr=visdom_addr, visdom_port=visdom_port) if dashboard else NullMonitor()
        whitelist = set(open(whitelist_file).read().splitlines(keepends=False)) if whitelist_file else None
        tac_parameters = TACParameters(
            min_nb_agents=nb_agents,
            money_endowment=money_endowment,
            nb_goods=nb_goods,
            tx_fee=tx_fee,
            base_good_endowment=base_good_endowment,
            lower_bound_factor=lower_bound_factor,
            upper_bound_factor=upper_bound_factor,
            start_time=dateutil.parser.parse(str(start_time)),
            registration_timeout=registration_timeout,
            competition_timeout=competition_timeout,
            inactivity_timeout=inactivity_timeout,
            whitelist=whitelist,
            data_output_dir=data_output_dir,
            version_id=version_id
        )
        agent = ControllerAgent(name=name,
                                oef_addr=oef_addr,
                                oef_port=oef_port,
                                tac_parameters=tac_parameters,
                                monitor=monitor)
        agent.start()

    except Exception as e:
        logger.exception(e)
    except KeyboardInterrupt:
        logger.debug("Controller interrupted...")
    finally:
        if agent is not None:
            agent.stop()
            agent.teardown()


if __name__ == '__main__':
    arguments = _parse_arguments()
    main(**arguments.__dict__)

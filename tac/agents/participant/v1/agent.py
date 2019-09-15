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

"""This module contains a base implementation of an agent for TAC."""

import logging
import time
from typing import Optional

from aea.agent import Agent
from aea.channel.oef import OEFMailBox
from aea.mail.base import Envelope
from tac.agents.participant.v1.base.game_instance import GameInstance
from tac.agents.participant.v1.base.handlers import ControllerHandler, DialogueHandler, OEFHandler
from tac.agents.participant.v1.base.strategy import Strategy
from tac.gui.dashboards.agent import AgentDashboard
from tac.platform.game.base import GamePhase

logger = logging.getLogger(__name__)


class ParticipantAgent(Agent):
    """The participant agent class implements a base agent for TAC."""

    def __init__(self, name: str,
                 oef_addr: str,
                 oef_port: int,
                 strategy: Strategy,
                 agent_timeout: float = 1.0,
                 max_reactions: int = 100,
                 services_interval: int = 10,
                 pending_transaction_timeout: int = 30,
                 dashboard: Optional[AgentDashboard] = None,
                 private_key_pem: Optional[str] = None,
                 debug: bool = False):
        """
        Initialize a participant agent.

        :param name: the name of the agent.
        :param oef_addr: the TCP/IP address of the OEF node.
        :param oef_port: the TCP/IP port of the OEF node.
        :param strategy: the strategy object that specify the behaviour during the competition.
        :param agent_timeout: the time in (fractions of) seconds to time out an agent between act and react.
        :param max_reactions: the maximum number of reactions (messages processed) per call to react.
        :param services_interval: the number of seconds between different searches.
        :param pending_transaction_timeout: the timeout for cleanup of pending negotiations and unconfirmed transactions.
        :param dashboard: a Visdom dashboard to visualize agent statistics during the competition.
        :param private_key_pem: the path to a private key in PEM format.
        :param debug: if True, run the agent in debug mode.
        """
        super().__init__(name, private_key_pem, agent_timeout, debug=debug)
        self.mailbox = OEFMailBox(self.crypto.public_key, oef_addr, oef_port)

        self._game_instance = GameInstance(name, strategy, self.mailbox.mail_stats, services_interval, pending_transaction_timeout, dashboard)
        self.max_reactions = max_reactions

        self.controller_handler = ControllerHandler(self.crypto, self.liveness, self.game_instance, self.mailbox, self.name)
        self.oef_handler = OEFHandler(self.crypto, self.liveness, self.game_instance, self.mailbox, self.name)
        self.dialogue_handler = DialogueHandler(self.crypto, self.liveness, self.game_instance, self.mailbox, self.name)

    @property
    def game_instance(self) -> GameInstance:
        """Get the game instance."""
        return self._game_instance

    def act(self) -> None:
        """
        Perform the agent's actions.

        :return: None
        """
        if self.game_instance.game_phase == GamePhase.PRE_GAME:
            self.oef_handler.search_for_tac()
        if self.game_instance.game_phase == GamePhase.GAME:
            if self.game_instance.is_time_to_update_services():
                self.oef_handler.update_services()
            if self.game_instance.is_time_to_search_services():
                self.oef_handler.search_services()

    def react(self) -> None:
        """
        React to incoming events.

        :return: None
        """
        counter = 0
        while (not self.mailbox.inbox.empty() and counter < self.max_reactions):
            counter += 1
            envelope = self.mailbox.inbox.get_nowait()  # type: Optional[Envelope]

            if envelope is not None:
                logger.debug("processing message of protocol={}".format(envelope.protocol_id))
                if envelope.protocol_id == "oef":
                    self.oef_handler.handle_oef_message(envelope)
                elif envelope.protocol_id == "tac":
                    self.controller_handler.handle_controller_message(envelope)
                elif envelope.protocol_id == "fipa":
                    self.dialogue_handler.handle_dialogue_message(envelope)
                else:
                    logger.warning("Message type not recognized: sender={}".format(envelope.sender))

    def update(self) -> None:
        """
        Update the state of the agent.

        :return: None
        """
        self.game_instance.transaction_manager.cleanup_pending_transactions()

    def stop(self) -> None:
        """
        Stop the agent.

        :return: None
        """
        super().stop()
        self.game_instance.stop()

    def start(self, rejoin: bool = False) -> None:
        """
        Start the agent.

        :return: None
        """
        try:
            self.oef_handler.rejoin = rejoin
            super().start()
            self.oef_handler.rejoin = False
            return
        except Exception as e:
            logger.exception(e)
            logger.debug("Stopping the agent...")
            self.stop()

        # here only if an error occurred
        logger.debug("Trying to rejoin in 5 seconds...")
        time.sleep(5.0)
        self.start(rejoin=True)

    def setup(self) -> None:
        """Set up the agent."""

    def teardown(self) -> None:
        """Tear down the agent."""

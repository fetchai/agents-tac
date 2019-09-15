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
from tac.gui.dashboards.agent import AgentDashboard

logger = logging.getLogger(__name__)


class ParticipantAgent(Agent):
    """The participant agent class implements a base agent for TAC."""

    def __init__(self, name: str,
                 oef_addr: str,
                 oef_port: int,
                 dashboard: Optional[AgentDashboard] = None,
                 private_key_pem: Optional[str] = None,
                 agent_timeout: Optional[float] = 1.0,
                 debug: bool = False):
        """
        Initialize a participant agent.

        :param name: the name of the agent.
        :param oef_addr: the TCP/IP address of the OEF node.
        :param oef_port: the TCP/IP port of the OEF node.
        :param agent_timeout: the time in (fractions of) seconds to time out an agent between act and react.
        :param dashboard: a Visdom dashboard to visualize agent statistics during the competition.
        :param private_key_pem: the path to a private key in PEM format.
        :param debug: if True, run the agent in debug mode.
        """
        super().__init__(name, oef_addr, oef_port, private_key_pem, agent_timeout, debug=debug)
        self.mailbox = OEFMailBox(self.crypto.public_key, oef_addr, oef_port)

    def act(self) -> None:
        """
        Perform the agent's actions.

        :return: None
        """
        for behaviour in self.behaviours.values():
            behaviour.run()

    def react(self) -> None:
        """
        React to incoming events.

        :return: None
        """
        counter = 0
        while (not self.mailbox.inbox.empty() and counter < self.max_reactions):
            counter += 1
            msg = self.mailbox.inbox.get_nowait()  # type: Envelope
            logger.debug("processing message of protocol={}".format(msg.protocol_id))
            handler = self.handlers[msg.protocol_id]
            handler.handle(msg)

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

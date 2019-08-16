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

"""
This module contains the classes which define the reactions of an agent.

- OEFReactions: The OEFReactions class defines the reactions of an agent towards the OEF.
"""

import logging

from tac.agents.v1.agent import Liveness
from tac.agents.v1.mail.base import MailBox
from tac.agents.v1.mail.messages import Message
from tac.helpers.crypto import Crypto
from tac.platform.controller.interfaces import OEFReactionInterface

logger = logging.getLogger(__name__)


class OEFReactions(OEFReactionInterface):
    """The OEFReactions class defines the reactions of an agent towards the OEF."""

    def __init__(self, crypto: Crypto, liveness: Liveness, mailbox: MailBox, agent_name: str) -> None:
        """
        Instantiate the OEFReactions.

        :param crypto: the crypto module
        :param liveness: the liveness module
        :param mailbox: the mailbox of the agent
        :param agent_name: the agent name

        :return: None
        """
        self.crypto = crypto
        self.liveness = liveness
        self.mailbox = mailbox
        self.agent_name = agent_name

    def on_oef_error(self, oef_error: Message) -> None:
        """
        Handle an OEF error message.

        :param oef_error: the oef error

        :return: None
        """
        logger.error("[{}]: Received OEF error: answer_id={}, operation={}"
                     .format(self.agent_name, oef_error.get("id"), oef_error.get("operation")))

    def on_dialogue_error(self, dialogue_error: Message) -> None:
        """
        Handle a dialogue error message.

        :param dialogue_error: the dialogue error message

        :return: None
        """
        logger.error("[{}]: Received Dialogue error: answer_id={}, dialogue_id={}, origin={}"
                     .format(self.agent_name, dialogue_error.get("id"), dialogue_error.get("dialogue_id"), dialogue_error.get("origin")))

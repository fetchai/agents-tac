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

"""This module contains an OEF agent for testing."""

from typing import List

from oef.agents import OEFAgent
from oef.messages import PROPOSE_TYPES, BaseMessage, Message, CFP, CFP_TYPES, Propose, Accept, Decline
from oef.uri import Context


class TOEFAgent(OEFAgent):
    """An OEF agent for testing."""

    def __init__(self, *args, **kwargs):
        """Initialize."""
        super().__init__(*args, **kwargs)
        self.messages = []  # type: List[BaseMessage]

    def on_message(self, msg_id: int, dialogue_id: int, origin: str, content: bytes) -> None:
        """
        On message handler.

        :param msg_id: the message id
        :param dialogue_id: the dialogue id
        :param origin: the origin public key
        :param content: the message content
        :return: None
        """
        self.messages.append(Message(msg_id, dialogue_id, origin, content, Context()))

    def on_cfp(self, msg_id: int, dialogue_id: int, origin: str, target: int, query: CFP_TYPES) -> None:
        """
        On cfp handler.

        :param msg_id: the message id
        :param dialogue_id: the dialogue id
        :param origin: the origin public key
        :param target: the message target
        :param query: the query object
        :return: None
        """
        self.messages.append(CFP(msg_id, dialogue_id, origin, target, query, Context()))

    def on_propose(self, msg_id: int, dialogue_id: int, origin: str, target: int, proposals: PROPOSE_TYPES) -> None:
        """
        On propose handler.

        :param msg_id: the message id
        :param dialogue_id: the dialogue id
        :param origin: the origin public key
        :param target: the message target
        :param proposals: the proposals
        :return: None
        """
        self.messages.append(Propose(msg_id, dialogue_id, origin, target, proposals, Context()))

    def on_accept(self, msg_id: int, dialogue_id: int, origin: str, target: int) -> None:
        """
        On accept handler.

        :param msg_id: the message id
        :param dialogue_id: the dialogue id
        :param origin: the origin public key
        :param target: the message target
        :return: None
        """
        self.messages.append(Accept(msg_id, dialogue_id, origin, target, Context()))

    def on_decline(self, msg_id: int, dialogue_id: int, origin: str, target: int) -> None:
        """
        On message handler.

        :param msg_id: the message id
        :param dialogue_id: the dialogue id
        :param origin: the origin public key
        :param target: the message target
        :return: None
        """
        self.messages.append(Decline(msg_id, dialogue_id, origin, target, Context()))

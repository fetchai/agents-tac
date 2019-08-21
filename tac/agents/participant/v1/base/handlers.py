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
This module contains the message handler classes.

- DialogueHandler: Handle the dialogue with another agent.
- ControllerHandler: Handle the message exchange with the controller.
- OEFHandler: Handle the message exchange with the OEF.
"""

import logging
from typing import Any

from tac.aea.agent import Liveness
from tac.aea.crypto.base import Crypto
from tac.aea.mail.base import MailBox, Envelope
from tac.aea.protocols.base.message import Message
from tac.aea.protocols.default.serialization import DefaultSerializer
from tac.aea.protocols.fipa.serialization import FIPASerializer
from tac.aea.protocols.oef.message import OEFMessage
from tac.aea.protocols.oef.serialization import OEFSerializer
from tac.agents.participant.v1.base.actions import DialogueActions, ControllerActions, OEFActions
from tac.agents.participant.v1.base.game_instance import GameInstance
from tac.agents.participant.v1.base.reactions import DialogueReactions, ControllerReactions, OEFReactions
from tac.platform.game.base import GamePhase
from tac.platform.protocol import Error, TransactionConfirmation, StateUpdate, Response, GameData, Cancelled

logger = logging.getLogger(__name__)

Action = Any


class DialogueHandler(DialogueActions, DialogueReactions):
    """Handle the dialogue with another agent."""

    def __init__(self, crypto: Crypto, liveness: Liveness, game_instance: GameInstance, mailbox: MailBox, agent_name: str):
        """
        Instantiate the DialogueHandler.

        :param crypto: the crypto module
        :param liveness: the liveness module
        :param game_instance: the game instance
        :param mailbox: the mailbox
        :param agent_name: the agent name
        """
        DialogueActions.__init__(self, crypto, liveness, game_instance, mailbox, agent_name)
        DialogueReactions.__init__(self, crypto, liveness, game_instance, mailbox, agent_name)

    def handle_dialogue_message(self, envelope: Envelope) -> None:
        """
        Handle messages from the other agents.

        The agents expect a response.

        :param envelope: the envelope.

        :return: None
        """
        message = FIPASerializer().decode(envelope.message)  # type: Message
        logger.debug("Handling Dialogue message. type={}".format(type(message.get("performative"))))
        if self.dialogues.is_belonging_to_registered_dialogue(message, self.crypto.public_key, envelope.sender):
            self.on_existing_dialogue(message, envelope.sender)
        elif self.dialogues.is_permitted_for_new_dialogue(message, self.game_instance.game_configuration.agent_pbks, envelope.sender):
            self.on_new_dialogue(message, envelope.sender)
        else:
            self.on_unidentified_dialogue(message, envelope.sender)


class ControllerHandler(ControllerActions, ControllerReactions):
    """Handle the message exchange with the controller."""

    def __init__(self, crypto: Crypto, liveness: Liveness, game_instance: GameInstance, mailbox: MailBox, agent_name: str):
        """
        Instantiate the ControllerHandler.

        :param crypto: the crypto module
        :param liveness: the liveness module
        :param game_instance: the game instance
        :param mailbox: the mailbox
        :param agent_name: the agent name
        """
        ControllerActions.__init__(self, crypto, liveness, game_instance, mailbox, agent_name)
        ControllerReactions.__init__(self, crypto, liveness, game_instance, mailbox, agent_name)

    def handle_controller_message(self, envelope: Envelope) -> None:
        """
        Handle messages from the controller.

        The controller does not expect a response for any of these messages.

        :param envelope: the controller message

        :return: None
        """
        assert envelope.protocol_id == "default"
        msg = DefaultSerializer().decode(envelope.message)
        response = Response.from_pb(msg.get("content"), envelope.sender, self.crypto)
        logger.debug("[{}]: Handling controller response. type={}".format(self.agent_name, type(response)))
        try:
            if envelope.sender != self.game_instance.controller_pbk:
                raise ValueError("The sender of the message is not the controller agent we registered with.")

            if isinstance(response, Error):
                self.on_tac_error(response)
            elif self.game_instance.game_phase == GamePhase.PRE_GAME:
                raise ValueError("We do not expect a controller agent message in the pre game phase.")
            elif self.game_instance.game_phase == GamePhase.GAME_SETUP:
                if isinstance(response, GameData):
                    self.on_start(response)
                elif isinstance(response, Cancelled):
                    self.on_cancelled()
            elif self.game_instance.game_phase == GamePhase.GAME:
                if isinstance(response, TransactionConfirmation):
                    self.on_transaction_confirmed(response)
                elif isinstance(response, Cancelled):
                    self.on_cancelled()
                elif isinstance(response, StateUpdate):
                    self.on_state_update(response)
            elif self.game_instance.game_phase == GamePhase.POST_GAME:
                raise ValueError("We do not expect a controller agent message in the post game phase.")
        except ValueError as e:
            logger.warning(str(e))


class OEFHandler(OEFActions, OEFReactions):
    """Handle the message exchange with the OEF."""

    def __init__(self, crypto: Crypto, liveness: Liveness, game_instance: GameInstance, mailbox: MailBox, agent_name: str, rejoin: bool = False):
        """
        Instantiate the OEFHandler.

        :param crypto: the crypto module
        :param liveness: the liveness module
        :param game_instance: the game instance
        :param mailbox: the mailbox
        :param agent_name: the agent name
        :param rejoin: boolean indicating whether the agent will rejoin the TAC if losing connection
        """
        OEFActions.__init__(self, crypto, liveness, game_instance, mailbox, agent_name)
        OEFReactions.__init__(self, crypto, liveness, game_instance, mailbox, agent_name, rejoin)

    def handle_oef_message(self, envelope: Envelope) -> None:
        """
        Handle messages from the oef.

        The oef does not expect a response for any of these messages.

        :param envelope: the OEF message

        :return: None
        """
        logger.debug("[{}]: Handling OEF message. type={}".format(self.agent_name, type(envelope)))
        assert envelope.protocol_id == "oef"
        oef_message = OEFSerializer().decode(envelope.message)
        oef_type = oef_message.get("type")
        if oef_type == OEFMessage.Type.SEARCH_RESULT:
            self.on_search_result(oef_message)
        elif oef_type == OEFMessage.Type.OEF_ERROR:
            self.on_oef_error(oef_message)
        elif oef_type == OEFMessage.Type.DIALOGUE_ERROR:
            self.on_dialogue_error(oef_message)
        else:
            logger.warning("[{}]: OEF Message type not recognized: {}.".format(self.agent_name, oef_type))

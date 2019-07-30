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
from typing import Any, Union

from oef.messages import CFP, Decline, Propose, Accept, Message as SimpleMessage, \
    SearchResult, OEFErrorMessage, DialogueErrorMessage

from tac.agents.v1.agent import Liveness
from tac.agents.v1.base.actions import DialogueActions, ControllerActions, OEFActions
from tac.agents.v1.base.game_instance import GameInstance, GamePhase
from tac.agents.v1.base.reactions import DialogueReactions, ControllerReactions, OEFReactions
from tac.agents.v1.mail import OutBox
from tac.helpers.crypto import Crypto
from tac.platform.protocol import Error, TransactionConfirmation, StateUpdate, Response, GameData, Cancelled

logger = logging.getLogger(__name__)

Action = Any
OEFMessage = Union[SearchResult, OEFErrorMessage, DialogueErrorMessage]
ControllerMessage = SimpleMessage
AgentMessage = Union[SimpleMessage, CFP, Propose, Accept, Decline]
Message = Union[OEFMessage, ControllerMessage, AgentMessage]


class DialogueHandler(DialogueActions, DialogueReactions):
    """Handle the dialogue with another agent."""

    def __init__(self, crypto: Crypto, liveness: Liveness, game_instance: GameInstance, out_box: OutBox, agent_name: str):
        """
        Instantiate the DialogueHandler.

        :param crypto: the crypto module
        :param liveness: the liveness module
        :param game_instance: the game instance
        :param out_box: the outbox
        :param agent_name: the agent name
        """
        DialogueActions.__init__(self, crypto, liveness, game_instance, out_box, agent_name)
        DialogueReactions.__init__(self, crypto, liveness, game_instance, out_box, agent_name)

    def handle_dialogue_message(self, msg: AgentMessage) -> None:
        """
        Handle messages from the other agents.

        The agents expect a response.

        :param msg: the agent message

        :return: None
        """
        logger.debug("Handling Dialogue message. type={}".format(type(msg)))
        if self.dialogues.is_belonging_to_registered_dialogue(msg, self.crypto.public_key):
            self.on_existing_dialogue(msg)
        elif self.dialogues.is_permitted_for_new_dialogue(msg, self.game_instance.game_configuration.agent_pbks):
            self.on_new_dialogue(msg)
        else:
            self.on_unidentified_dialogue(msg)


class ControllerHandler(ControllerActions, ControllerReactions):
    """Handle the message exchange with the controller."""

    def __init__(self, crypto: Crypto, liveness: Liveness, game_instance: GameInstance, out_box: 'OutBox', agent_name: str):
        """
        Instantiate the ControllerHandler.

        :param crypto: the crypto module
        :param liveness: the liveness module
        :param game_instance: the game instance
        :param out_box: the outbox
        :param agent_name: the agent name
        """
        ControllerActions.__init__(self, crypto, liveness, game_instance, out_box, agent_name)
        ControllerReactions.__init__(self, crypto, liveness, game_instance, out_box, agent_name)

    def handle_controller_message(self, msg: ControllerMessage) -> None:
        """
        Handle messages from the controller.

        The controller does not expect a response for any of these messages.

        :param msg: the controller message

        :return: None
        """
        response = Response.from_pb(msg.msg, msg.destination, self.crypto)
        logger.debug("[{}]: Handling controller response. type={}".format(self.agent_name, type(response)))
        try:
            if msg.destination != self.game_instance.controller_pbk:
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

    def __init__(self, crypto: Crypto, liveness: Liveness, game_instance: GameInstance, out_box: 'OutBox', agent_name: str, rejoin: bool = False):
        """
        Instantiate the OEFHandler.

        :param crypto: the crypto module
        :param liveness: the liveness module
        :param game_instance: the game instance
        :param out_box: the outbox
        :param agent_name: the agent name
        :param rejoin: boolean indicating whether the agent will rejoin the TAC if losing connection
        """
        OEFActions.__init__(self, crypto, liveness, game_instance, out_box, agent_name)
        OEFReactions.__init__(self, crypto, liveness, game_instance, out_box, agent_name, rejoin)

    def handle_oef_message(self, msg: OEFMessage) -> None:
        """
        Handle messages from the oef.

        The oef does not expect a response for any of these messages.

        :param msg: the OEF message

        :return: None
        """
        logger.debug("[{}]: Handling OEF message. type={}".format(self.agent_name, type(msg)))
        if isinstance(msg, SearchResult):
            self.on_search_result(msg)
        elif isinstance(msg, OEFErrorMessage):
            self.on_oef_error(msg)
        elif isinstance(msg, DialogueErrorMessage):
            self.on_dialogue_error(msg)
        else:
            logger.warning("[{}]: OEF Message type not recognized.".format(self.agent_name))

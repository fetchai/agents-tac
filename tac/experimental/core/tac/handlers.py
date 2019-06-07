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
import logging
from typing import Any, Union

from oef.messages import CFP, Decline, Propose, Accept, Message as SimpleMessage, \
    SearchResult, OEFErrorMessage, DialogueErrorMessage

from tac.experimental.core.agent import Liveness
from tac.experimental.core.tac.actions import DialogueActions, ControllerActions, OEFActions
from tac.experimental.core.tac.dialogues import Dialogues, DialogueLabel
from tac.experimental.core.tac.game_instance import GameInstance, GamePhase
from tac.experimental.core.mail import OutBox
from tac.helpers.crypto import Crypto
from tac.protocol import Error, TransactionConfirmation, StateUpdate, Response, GameData, Cancelled

logger = logging.getLogger(__name__)

Action = Any
OEFMessage = Union[SearchResult, OEFErrorMessage, DialogueErrorMessage]
ControllerMessage = SimpleMessage
AgentMessage = Union[SimpleMessage, CFP, Propose, Accept, Decline]
Message = Union[OEFMessage, ControllerMessage, AgentMessage]


class DialogueHandler(DialogueActions):
    """
    Handles the dialogue with another agent.
    """

    def __init__(self, crypto: Crypto, liveness: Liveness, game_instance: GameInstance, out_box: OutBox, name: str):
        self.dialogues = Dialogues()
        super().__init__(crypto, liveness, game_instance, out_box, name, self.dialogues)

    def handle_dialogue_message(self, msg: AgentMessage) -> None:
        """
        Handles messages from the other agents.

        The agents expect a response.

        :return: None
        """
        logger.debug("Handling Dialogue message. type={}".format(type(msg)))
        dialogue_label = DialogueLabel(msg.dialogue_id, msg.destination)
        if self.dialogues.is_dialogue_registered(dialogue_label):
            dialogue = self.dialogues.get_dialogue(dialogue_label)
        else:
            dialogue = self.dialogues.new_dialogue(msg)

        if not dialogue.check_message(msg):
            self.out_box._mail_box.out_queue.put(DialogueErrorMessage)
        else:
            response = dialogue.dispatch_to_handler(msg)
            self.out_box._mail_box.out_queue.put(response)


class ControllerHandler(ControllerActions):

    def __init__(self, crypto: Crypto, liveness: Liveness, game_instance: GameInstance, out_box: 'OutBox', name: str):
        super().__init__(crypto, liveness, game_instance, out_box, name)

    def handle_controller_message(self, msg: ControllerMessage) -> None:
        """
        Handles messages from the controller.

        The controller does not expect a response for any of these messages.

        :return: None
        """
        response = Response.from_pb(msg.msg, msg.destination, self.crypto)  # TODO this is already created once above!
        logger.debug("[{}]: Handling controller response. type={}".format(self.name, type(response)))
        try:
            if msg.destination != self.game_instance.controller_pbk:
                raise ValueError("The sender of the message is not a controller agent.")

            if isinstance(response, Error):
                self.on_tac_error(response)
            elif self.game_instance.game_phase == GamePhase.PRE_GAME:
                raise ValueError("We do not except a controller agent message in the pre game phase.")
            elif self.game_instance.game_phase == GamePhase.GAME_SETUP:
                if isinstance(response, GameData):
                    self.game_instance.init(response)
                    self.game_instance._game_phase = GamePhase.GAME
                    self.on_start()
                elif isinstance(response, Cancelled):
                    self.game_instance._game_phase = GamePhase.POST_GAME
                    self.on_cancelled()
            elif self.game_instance.game_phase == GamePhase.GAME:
                if isinstance(response, TransactionConfirmation):
                    self.on_transaction_confirmed(response)
                elif isinstance(response, Cancelled):
                    self.game_instance._game_phase = GamePhase.POST_GAME
                    self.on_cancelled()
                elif isinstance(response, StateUpdate):
                    self.on_state_update(response)
            elif self.game_instance.game_phase == GamePhase.POST_GAME:
                raise ValueError("We do not except a controller agent message in the post game phase.")
        except ValueError as e:
            logger.warning(str(e))


class OEFHandler(OEFActions):

    def __init__(self, crypto: Crypto, liveness: Liveness, game_instance: GameInstance, out_box: 'OutBox', name: str):
        super().__init__(crypto, liveness, game_instance, out_box, name)

    def handle_oef_message(self, msg: OEFMessage) -> None:
        """
        Handles messages from the oef.

        The oef does not expect a response for any of these messages.

        :return: None
        """
        logger.debug("[{}]: Handling OEF message. type={}".format(self.name, type(msg)))
        if isinstance(msg, SearchResult):
            self.on_search_result(msg)
        elif isinstance(msg, OEFErrorMessage):
            self.on_oef_error(msg)
        elif isinstance(msg, DialogueErrorMessage):
            self.on_dialogue_error(msg)
        else:
            logger.warning("[{}]: OEF Message type not recognized.".format(self.name))

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
from typing import List

from oef.messages import Message as SearchResult, OEFErrorMessage, DialogueErrorMessage

from tac.experimental.core.agent import Liveness
from tac.experimental.core.tac.dialogues import Dialogues, Dialogue
from tac.experimental.core.tac.interfaces import ControllerReactionInterface, OEFSearchReactionInterface, DialogueInterface
from tac.experimental.core.tac.game_instance import GameInstance, GamePhase
from tac.experimental.core.mail import OutBox, OutContainer
from tac.helpers.crypto import Crypto
from tac.protocol import Error, TransactionConfirmation, StateUpdate, Register

logger = logging.getLogger(__name__)


class ControllerReactions(ControllerReactionInterface):

    def __init__(self, crypto: Crypto, liveness: Liveness, game_instance: GameInstance, out_box: 'OutBox', name: str):
        self.crypto = crypto
        self.liveness = liveness
        self.game_instance = game_instance
        self.out_box = out_box
        self.name = name

    def on_dialogue_error(self, dialogue_error: DialogueErrorMessage):
        pass

    def on_start(self) -> None:
        pass

    def on_transaction_confirmed(self, tx_confirmation: TransactionConfirmation) -> None:
        pass

    def on_state_update(self, agent_state: StateUpdate) -> None:
        pass

    def on_cancelled(self) -> None:
        """
        Handle the cancellation of the competition from the TAC controller.

        :return: None
        """
        logger.debug("[{}]: Received cancellation from the controller.".format(self.name))
        self.liveness._is_stopped = True

    def on_tac_error(self, error: Error) -> None:
        pass


class OEFReactions(OEFSearchReactionInterface):

    def __init__(self, crypto: Crypto, liveness: Liveness, game_instance: GameInstance, out_box: 'OutBox', name: str):
        self.crypto = crypto
        self.liveness = liveness
        self.game_instance = game_instance
        self.out_box = out_box
        self.name = name

    def on_search_result(self, search_result: SearchResult):
        """Split the search results from the OEF."""
        search_id = search_result.msg_id
        if search_id in self.game_instance.search_ids.for_tac:
            self._on_contoller_search_result(search_result)
        else:
            self._on_services_search_result(search_result.agents)

    def on_oef_error(self, oef_error: OEFErrorMessage):
        logger.debug("[{}]: Received OEF error: answer_id={}, operation={}".format(self.nameoef_error.answer_id, oef_error.operation))

    def on_dialogue_error(self, dialogue_error: DialogueErrorMessage):
        logger.debug("[{}]: Received Dialogue error: answer_id={}, dialogue_id={}, origin={}".format(self.name, dialogue_error.answer_id, dialogue_error.dialogue_id, dialogue_error.origin))

    def _on_controller_search_result(self, search_result: SearchResult) -> None:
        """
        Process the search result for a controller.

        :return: None
        """
        if len(search_result.agents) == 0:
            logger.debug("[{}]: Couldn't find the TAC controller.".format(self.name))
            self.liveness._is_stopped = True
        elif len(search_result.agents) > 1:
            logger.debug("[{}]: Found more than one TAC controller.".format(self.name))
            self.liveness._is_stopped = True
        else:
            logger.debug("[{}]: Found the TAC controller.".format(self.name))
            controller_pbk = search_result.agents[0]
            self._register_to_tac(controller_pbk)

    def _on_services_search_result(self, search_result: SearchResult) -> None:
        """
        Process the search result for services.

        :return: None
        """

    def _react_to_search_results(self, sender_id: str, agent_pbks: List[str]) -> None:
        pass

    def _register_to_tac(self, controller_pbk: str) -> None:
        """
        Register to active TAC Controller.

        :param controller_pbk: the public key of the controller.

        :return: None
        """
        self.game_instance.controller_pbk = controller_pbk
        self.game_instance._game_phase = GamePhase.GAME_SETUP
        msg = Register(self.crypto.public_key, self.crypto, self.name).serialize()
        self.out_box.out_queue.put(OutContainer(message=msg, message_id=0, dialogue_id=0, destination=controller_pbk))


class DialogueReactions(DialogueInterface):
    """
    Implements a basic dialogue interface.
    """

    def __init__(self, crypto: Crypto, liveness: Liveness, game_instance: GameInstance, out_box: OutBox, name: str, dialogues: Dialogues):
        self.crypto = crypto
        self.liveness = liveness
        self.game_instance = game_instance
        self.out_box = out_box
        self.name = name
        self.dialogues = dialogues

    def on_new_dialogue(self, msg) -> Dialogue:
        pass

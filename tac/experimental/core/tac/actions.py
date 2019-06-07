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
from oef.query import Query, Constraint, GtEq

from tac.experimental.core.agent import Liveness
from tac.experimental.core.tac.dialogues import Dialogues, Dialogue
from tac.experimental.core.tac.interfaces import ControllerInterface, OEFSearchInterface, DialogueInterface
from tac.experimental.core.tac.game_instance import GameInstance, GamePhase
from tac.experimental.core.mail import OutBox, OutContainer
from tac.helpers.crypto import Crypto
from tac.protocol import Error, TransactionConfirmation, StateUpdate, Register

logger = logging.getLogger(__name__)


class ControllerActions(ControllerInterface):

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


class OEFActions(OEFSearchInterface):

    def __init__(self, crypto: Crypto, liveness: Liveness, game_instance: GameInstance, out_box: 'OutBox', name: str):
        self.crypto = crypto
        self.liveness = liveness
        self.game_instance = game_instance
        self.out_box = out_box
        self.name = name

    def search_for_tac(self) -> None:
        """
        Search for active TAC Controller.

        We assume that the controller is registered as a service with the 'tac' data model
        and with an attribute version = 1.

        :return: None
        """
        query = Query([Constraint("version", GtEq(1))])
        search_id = self.game_instance.get_next_search_id()
        self.out_box.out_queue.put(OutContainer(query=query, search_id=search_id))

    def on_search_result(self, search_result: SearchResult):
        """Process a search result from the OEF."""
        search_id = search_result.msg_id
        if search_id in self.game_instance.search_ids_for_tac:
            controller_pbk = search_result.agents[0]
            if len(search_result.agents) == 0:
                logger.debug("[{}]: Couldn't find the TAC controller.".format(self.name))
                self.liveness._is_stopped = True
            elif len(search_result.agents) > 1:
                logger.debug("[{}]: Found more than one TAC controller.".format(self.name))
                self.liveness._is_stopped = True
            else:
                self._register_to_tac(controller_pbk)
        else:
            self._react_to_search_results(search_id, search_result.agents)

    def on_oef_error(self, oef_error: OEFErrorMessage) -> None:
        pass

    def on_dialogue_error(self, dialogue_error: DialogueErrorMessage):
        pass

    def _react_to_search_results(self, sender_id: str, agent_pbks: List[str]) -> None:
        pass

    def _register_to_tac(self, tac_controller_pbk: str) -> None:
        """
        Register to active TAC Controller.

        :param tac_controller_pbk: the public key of the controller.

        :return: None
        :raises AssertionError: if the agent is already registered.
        """
        self.game_instance.controller_pbk = tac_controller_pbk
        self.game_instance._game_phase = GamePhase.GAME_SETUP
        msg = Register(self.crypto.public_key, self.crypto, self.name).serialize()
        self.out_box.out_queue.put(OutContainer(msg=msg, msg_id=0, dialogue_id=0, destination=tac_controller_pbk))


class DialogueActions(DialogueInterface):
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

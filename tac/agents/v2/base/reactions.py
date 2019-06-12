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
from typing import List, Union, Optional

from oef.messages import CFP, Propose, Accept, Decline, Message as ByteMessage, SearchResult, OEFErrorMessage, DialogueErrorMessage

from tac.agents.v2.agent import Liveness
from tac.agents.v2.base.behaviours import FIPABehaviour
from tac.agents.v2.base.dialogues import Dialogue
from tac.agents.v2.base.interfaces import ControllerReactionInterface, OEFSearchReactionInterface, DialogueReactionInterface
from tac.agents.v2.base.game_instance import GameInstance, GamePhase
from tac.agents.v2.mail import OutBox, OutContainer
from tac.helpers.crypto import Crypto
from tac.helpers.misc import TAC_SUPPLY_DATAMODEL_NAME
from tac.platform.protocol import Error, ErrorCode, GameData, TransactionConfirmation, StateUpdate, Register

logger = logging.getLogger(__name__)

STARTING_MESSAGE_ID = 1
STARTING_MESSAGE_TARGET = 0

AgentMessage = Union[ByteMessage, CFP, Propose, Accept, Decline, OutContainer]


class ControllerReactions(ControllerReactionInterface):

    def __init__(self, crypto: Crypto, liveness: Liveness, game_instance: GameInstance, out_box: 'OutBox', name: str):
        self.crypto = crypto
        self.liveness = liveness
        self.game_instance = game_instance
        self.out_box = out_box
        self.name = name

    def on_dialogue_error(self, dialogue_error: DialogueErrorMessage):
        logger.debug("[{}]: Received Dialogue error: answer_id={}, dialogue_id={}, origin={}"
                     .format(self.name, dialogue_error.msg_id, dialogue_error.dialogue_id, dialogue_error.origin))

    def on_start(self, game_data: GameData) -> None:
        """
        Handle the 'start' event emitted by the controller.

        :return: None
        """
        logger.debug("[{}]: Received start event from the controller. Starting...".format(self.name))
        self.game_instance.init(game_data)
        self.game_instance._game_phase = GamePhase.GAME

    def on_transaction_confirmed(self, tx_confirmation: TransactionConfirmation) -> None:
        """
        Handles 'on transaction confirmed' event emitted by the controller.

        :param tx_confirmation: the transaction confirmation

        :return: None
        """
        logger.debug("[{}]: Received transaction confirmation from the controller: transaction_id={}".format(self.name, tx_confirmation.transaction_id))
        transaction = self.game_instance.lock_manager.pop_lock(tx_confirmation.transaction_id)
        self.game_instance._agent_state.update(transaction, self.game_instance.game_configuration.tx_fee)

    def on_state_update(self, agent_state: StateUpdate) -> None:
        pass

    def on_cancelled(self) -> None:
        """
        Handle the cancellation of the competition from the TAC controller.

        :return: None
        """
        logger.debug("[{}]: Received cancellation from the controller.".format(self.name))
        self.liveness._is_stopped = True
        self.game_instance._game_phase = GamePhase.POST_GAME

    def on_tac_error(self, error: Error) -> None:
        """
        Handles 'on tac error' event emitted by the controller.

        :param error: the error object

        :return: None
        """
        logger.error("[{}]: Received error from the controller. error_msg={}".format(self.name, error.error_msg))
        if error.error_code == ErrorCode.TRANSACTION_NOT_VALID:
            # if error in checking transaction, remove it from the pending transactions.
            start_idx_of_tx_id = len("Error in checking transaction: ")
            transaction_id = error.error_msg[start_idx_of_tx_id:]
            if transaction_id in self.game_instance.lock_manager.locks:
                self.game_instance.lock_manager.pop_lock(transaction_id)
            else:
                logger.warning("[{}]: Received error on unknown transaction id: {}".format(self.name, transaction_id))
            pass
        elif error.error_code == ErrorCode.TRANSACTION_NOT_MATCHING:
            pass
        elif error.error_code == ErrorCode.AGENT_PBK_ALREADY_REGISTERED or error.error_code == ErrorCode.AGENT_NAME_ALREADY_REGISTERED or error.error_code == ErrorCode.AGENT_NOT_REGISTERED:
            self.liveness._is_stopped = True
        elif error.error_code == ErrorCode.REQUEST_NOT_VALID or error.error_code == ErrorCode.GENERIC_ERROR:
            logger.warning("[{}]: Check last request sent and investigate!".format(self.name))


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
        logger.debug("[{}]: on search result: {} {}".format(self.name, search_id, search_result.agents))
        if search_id in self.game_instance.search.ids_for_tac:
            self._on_controller_search_result(search_result.agents)
        elif search_id in self.game_instance.search.ids_for_sellers:
            self._on_services_search_result(search_result.agents, is_searching_for_sellers=True)
        elif search_id in self.game_instance.search.ids_for_buyers:
            self._on_services_search_result(search_result.agents, is_searching_for_sellers=False)
        else:
            logger.debug("[{}]: Unknown search id: search_id={}".format(self.name, search_id))

    def on_oef_error(self, oef_error: OEFErrorMessage):
        logger.debug("[{}]: Received OEF error: answer_id={}, operation={}"
                     .format(self.name, oef_error.msg_id, oef_error.oef_error_operation))

    def on_dialogue_error(self, dialogue_error: DialogueErrorMessage):
        logger.debug("[{}]: Received Dialogue error: answer_id={}, dialogue_id={}, origin={}"
                     .format(self.name, dialogue_error.msg_id, dialogue_error.dialogue_id, dialogue_error.origin))

    def _on_controller_search_result(self, agent_pbks: List[str]) -> None:
        """
        Process the search result for a controller.

        :return: None
        """
        if len(agent_pbks) == 0:
            logger.debug("[{}]: Couldn't find the TAC controller.".format(self.name))
            self.liveness._is_stopped = True
        elif len(agent_pbks) > 1:
            logger.debug("[{}]: Found more than one TAC controller.".format(self.name))
            self.liveness._is_stopped = True
        else:
            logger.debug("[{}]: Found the TAC controller.".format(self.name))
            controller_pbk = agent_pbks[0]
            self._register_to_tac(controller_pbk)

    def _on_services_search_result(self, agent_pbks: List[str], is_searching_for_sellers: bool) -> None:
        """
        Process the search result for services.

        :param agent_pbks: the agent pbks matching the search query
        :param is_searching_for_sellers: whether it is searching for sellers or not

        :return: None
        """
        agent_pbks = set(agent_pbks)
        agent_pbks.remove(self.crypto.public_key)
        agent_pbks = list(agent_pbks)
        searched_for = 'sellers' if is_searching_for_sellers else 'buyers'
        logger.debug("[{}]: Found potential {}: {}".format(self.name, searched_for, agent_pbks))

        query = self.game_instance.build_services_query(is_searching_for_sellers)
        if query is None:
            response = 'demanding' if is_searching_for_sellers else 'supplying'
            logger.debug("[{}]: No longer {} any goods...".format(self.name, response))
            return
        for agent_pbk in agent_pbks:
            dialogue = self.game_instance.dialogues.create(agent_pbk, self.crypto.public_key, not is_searching_for_sellers)
            cfp = CFP(STARTING_MESSAGE_ID, dialogue.dialogue_label.dialogue_id, agent_pbk, STARTING_MESSAGE_TARGET, query)
            logger.debug("[{}]: send_cfp_as_{}: msg_id={}, dialogue_id={}, destination={}, target={}, query={}"
                         .format(self.name, dialogue.role, cfp.msg_id, cfp.dialogue_id, cfp.destination, cfp.target, query))
            dialogue.outgoing_extend([cfp])
            self.out_box.out_queue.put(cfp)

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


class DialogueReactions(DialogueReactionInterface):
    """
    Implements a basic dialogue interface.
    """

    def __init__(self, crypto: Crypto, liveness: Liveness, game_instance: GameInstance, out_box: OutBox, name: str):
        self.crypto = crypto
        self.liveness = liveness
        self.game_instance = game_instance
        self.out_box = out_box
        self.name = name
        self.dialogues = game_instance.dialogues
        self.behaviour = FIPABehaviour(crypto, game_instance, name)

    def on_new_dialogue(self, msg: AgentMessage) -> None:
        """
        React to a new dialogue.
        """
        is_seller = msg.query.model.name == TAC_SUPPLY_DATAMODEL_NAME
        dialogue = self.dialogues.create(msg.destination, msg.destination, is_seller)
        logger.debug("[{}]: saving dialogue: dialogue_id={}".format(self.name, dialogue.dialogue_label.dialogue_id))
        results = self.handle(msg, dialogue)
        for result in results:
            self.out_box.out_queue.put(result)

    def on_existing_dialogue(self, msg: AgentMessage) -> None:
        """
        React to an existing dialogue.
        """
        dialogue = self.dialogues.get_dialogue(msg, self.crypto.public_key)

        results = self.handle(msg, dialogue)
        # if not dialogue.is_message_consistent(msg):
        #     logger.debug("[{}]: this message is not consistent: {}".format(self.name, type(msg)))
        #     response = ByteMessage(msg.msg_id + 1, msg.dialogue_id, msg.destination, b'This message is not consistent with the dialogue.')
        # else:
        for result in results:
            self.out_box.out_queue.put(result)

    def on_unidentified_dialogue(self, msg: AgentMessage) -> None:
        """
        React to an unidentified dialogue.
        """
        logger.debug("[{}]: Unidentified dialogue.".format(self.name))
        result = ByteMessage(msg.msg_id + 1, msg.dialogue_id, msg.destination, b'This message belongs to an unidentified dialogue.')
        self.out_box.out_queue.put(result)

    def handle(self, msg: AgentMessage, dialogue: Dialogue) -> Optional[AgentMessage]:
        dialogue.incoming_extend([msg])
        if isinstance(msg, CFP):
            result = self.behaviour.on_cfp(msg, dialogue)
            results = [result]
        elif isinstance(msg, Propose):
            result = self.behaviour.on_propose(msg, dialogue)
            results = [result]
        elif isinstance(msg, Accept):
            result = self.behaviour.on_accept(msg, dialogue)
            results = [result]
        elif isinstance(msg, Decline):
            results = self.behaviour.on_decline(msg, dialogue)
        dialogue.outgoing_extend(results)
        return results

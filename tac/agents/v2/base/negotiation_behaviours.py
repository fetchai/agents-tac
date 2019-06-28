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
import pprint
import random
from typing import Union, List

from oef.messages import CFP, Decline, Propose, Accept
from oef.utils import Context

from tac.agents.v2.base.game_instance import GameInstance
from tac.agents.v2.base.dialogues import Dialogue
from tac.agents.v2.mail import OutContainer
from tac.agents.v2.base.helpers import generate_transaction_id
from tac.agents.v2.base.stats_manager import EndState
from tac.helpers.crypto import Crypto
from tac.platform.protocol import Transaction

logger = logging.getLogger(__name__)

STARTING_MESSAGE_ID = 1


class FIPABehaviour:
    """
    Specifies FIPA negotiation behaviours
    """

    def __init__(self, crypto: Crypto, game_instance: GameInstance, name: str):
        self._crypto = crypto
        self._game_instance = game_instance
        self._name = name

    @property
    def game_instance(self) -> GameInstance:
        return self._game_instance

    @property
    def crypto(self) -> Crypto:
        return self._crypto

    @property
    def name(self) -> str:
        return self._name

    def on_cfp(self, cfp: CFP, dialogue: Dialogue) -> Union[Propose, Decline]:
        """
        Handles cfp.

        :param cfp: the CFP
        :param dialogue: the dialogue
        :return: None
        """
        goods_description = self.game_instance.get_service_description(is_supply=dialogue.is_seller)
        new_msg_id = cfp.msg_id + 1
        if not cfp.query.check(goods_description):
            logger.debug("[{}]: Current holdings do not satisfy CFP query.".format(self.name))
            logger.debug("[{}]: sending to {} a Decline{}".format(self.name, cfp.destination,
                                                                  pprint.pformat({
                                                                      "msg_id": new_msg_id,
                                                                      "dialogue_id": cfp.dialogue_id,
                                                                      "origin": cfp.destination,
                                                                      "target": cfp.msg_id
                                                                  })))
            response = Decline(new_msg_id, cfp.dialogue_id, cfp.destination, cfp.msg_id, Context())
            self.game_instance.stats_manager.add_dialogue_endstate(EndState.DECLINED_CFP, dialogue.is_self_initiated)
        else:
            proposals = [random.choice(self.game_instance.get_proposals(cfp.query, dialogue.is_seller))]
            self.game_instance.lock_manager.store_proposals(proposals, new_msg_id, dialogue, cfp.destination, dialogue.is_seller, self.crypto)
            logger.debug("[{}]: sending to {} a Propose{}".format(self.name, cfp.destination,
                                                                  pprint.pformat({
                                                                      "msg_id": new_msg_id,
                                                                      "dialogue_id": cfp.dialogue_id,
                                                                      "origin": cfp.destination,
                                                                      "target": cfp.msg_id,
                                                                      "propose": proposals[0].values  # TODO fix if more than one proposal!
                                                                  })))
            response = Propose(new_msg_id, cfp.dialogue_id, cfp.destination, cfp.msg_id, proposals, Context())
        return response

    def on_propose(self, propose: Propose, dialogue: Dialogue) -> Union[Accept, Decline]:
        """
        Handles propose.

        :param propose: the Propose
        :param dialogue: the dialogue
        :return: None
        """

        logger.debug("[{}]: on propose as {}.".format(self.name, dialogue.role))
        proposal = propose.proposals[0]
        transaction_id = generate_transaction_id(self.crypto.public_key, propose.destination, dialogue.dialogue_label, dialogue.is_seller)
        transaction = Transaction.from_proposal(proposal,
                                                transaction_id,
                                                is_buyer=not dialogue.is_seller,
                                                counterparty=propose.destination,
                                                sender=self.crypto.public_key,
                                                crypto=self.crypto)
        new_msg_id = propose.msg_id + 1
        if self._is_profitable_transaction(transaction, dialogue):
            logger.debug("[{}]: Accepting propose (as {}).".format(self.name, dialogue.role))
            self.game_instance.lock_manager.add_lock(transaction, as_seller=dialogue.is_seller)
            self.game_instance.lock_manager.add_pending_acceptances(dialogue, new_msg_id, transaction)
            result = Accept(new_msg_id, propose.dialogue_id, propose.destination, propose.msg_id, Context())
        else:
            logger.debug("[{}]: Declining propose (as {})".format(self.name, dialogue.role))
            result = Decline(new_msg_id, propose.dialogue_id, propose.destination, propose.msg_id, Context())
            self.game_instance.stats_manager.add_dialogue_endstate(EndState.DECLINED_PROPOSE, dialogue.is_self_initiated)
        return result

    def _is_profitable_transaction(self, transaction: Transaction, dialogue: Dialogue) -> bool:
        """
        Is a profitable transaction?
        - apply all the locks for role.
        - check if the transaction is consistent with the locks (enough money/holdings)
        - check that we gain score.

        :param transaction: the transaction
        :param dialogue: the dialogue

        :return: True if the transaction is good (as stated above), False otherwise.
        """

        state_after_locks = self.game_instance.state_after_locks(dialogue.is_seller)

        if not state_after_locks.check_transaction_is_consistent(transaction, self.game_instance.game_configuration.tx_fee):
            logger.debug("[{}]: the proposed transaction is not consistent with the state after locks.".format(self.name))
            return False
        proposal_delta_score = state_after_locks.get_score_diff_from_transaction(transaction, self.game_instance.game_configuration.tx_fee)

        result = self.game_instance.strategy.is_acceptable_proposal(proposal_delta_score)
        logger.debug("[{}]: is good proposal for {}? {}: tx_id={}, "
                     "delta_score={}, amount={}"
                     .format(self.name, dialogue.role, result, transaction.transaction_id,
                             proposal_delta_score, transaction.amount))
        return result

    def on_decline(self, decline: Decline, dialogue: Dialogue) -> None:
        """
        On Decline handler.

        :param decline: the decline
        :param dialogue: the dialogue

        :return: None
        """
        logger.debug("[{}]: on_decline: msg_id={}, dialogue_id={}, origin={}, target={}"
                     .format(self.name, decline.msg_id, decline.dialogue_id, decline.destination, decline.target))

        if self.game_instance.strategy.is_world_modeling:
            if dialogue.dialogue_label in self.game_instance.lock_manager.pending_tx_proposals and \
                    decline.target in self.game_instance.lock_manager.pending_tx_proposals[dialogue.dialogue_label]:
                transaction = self.game_instance.lock_manager.pop_pending_proposal(dialogue, decline.target)
                self.game_instance.world_state.update_on_decline(transaction)

        transaction_id = generate_transaction_id(self.crypto.public_key, decline.destination, dialogue.dialogue_label, dialogue.is_seller)
        if transaction_id in self.game_instance.lock_manager.locks:
            self.game_instance.lock_manager.pop_lock(transaction_id)

        if decline.target == 1:
            self.game_instance.stats_manager.add_dialogue_endstate(EndState.DECLINED_CFP, dialogue.is_self_initiated)
        elif decline.target == 2:
            self.game_instance.stats_manager.add_dialogue_endstate(EndState.DECLINED_PROPOSE, dialogue.is_self_initiated)
        elif decline.target == 3:
            self.game_instance.stats_manager.add_dialogue_endstate(EndState.DECLINED_ACCEPT, dialogue.is_self_initiated)

        return None

    def on_accept(self, accept: Accept, dialogue: Dialogue) -> Union[List[Decline], List[Union[OutContainer, Accept]], List[OutContainer]]:
        """
        On Accept dispatcher.

        :param accept: the accept
        :param dialogue: the dialogue

        :return: None
        """
        logger.debug("[{}]: on_accept: msg_id={}, dialogue_id={}, origin={}, target={}"
                     .format(self.name, accept.msg_id, accept.dialogue_id, accept.destination, accept.target))

        if dialogue.dialogue_label in self.game_instance.lock_manager.pending_tx_acceptances \
                and accept.target in self.game_instance.lock_manager.pending_tx_acceptances[dialogue.dialogue_label]:
            results = self._on_match_accept(accept, dialogue)
        else:
            results = self._on_initial_accept(accept, dialogue)
        return results

    def _on_initial_accept(self, accept: Accept, dialogue: Dialogue) -> Union[List[Decline], List[Union[OutContainer, Accept]]]:
        """
        Initial Accept handler.

        :param accept: the accept
        :param dialogue: the dialogue

        :return: None
        """
        transaction = self.game_instance.lock_manager.pop_pending_proposal(dialogue, accept.target)
        new_msg_id = accept.msg_id + 1
        results = []
        if self._is_profitable_transaction(transaction, dialogue):
            if self.game_instance.strategy.is_world_modeling:
                self.game_instance.world_state.update_on_accept(transaction)
            logger.debug("[{}]: Locking the current state (as {}).".format(self.name, dialogue.role))
            self.game_instance.lock_manager.add_lock(transaction, as_seller=dialogue.is_seller)
            results.append(OutContainer(message=transaction.serialize(), message_id=STARTING_MESSAGE_ID, dialogue_id=accept.dialogue_id, destination=self.game_instance.controller_pbk))
            results.append(Accept(new_msg_id, accept.dialogue_id, accept.destination, accept.msg_id, Context()))
        else:
            logger.debug("[{}]: Decline the accept (as {}).".format(self.name, dialogue.role))
            results.append(Decline(new_msg_id, accept.dialogue_id, accept.destination, accept.msg_id, Context()))
            self.game_instance.stats_manager.add_dialogue_endstate(EndState.DECLINED_ACCEPT, dialogue.is_self_initiated)
        return results

    def _on_match_accept(self, accept: Accept, dialogue: Dialogue) -> List[OutContainer]:
        """
        Match accept handler.

        :param accept: the accept
        :param dialogue: the dialogue

        :return: None
        """
        logger.debug("[{}]: on match accept".format(self.name))
        results = []
        transaction = self.game_instance.lock_manager.pop_pending_acceptances(dialogue, accept.target)
        results.append(OutContainer(message=transaction.serialize(), message_id=STARTING_MESSAGE_ID, dialogue_id=accept.dialogue_id, destination=self.game_instance.controller_pbk))
        return results

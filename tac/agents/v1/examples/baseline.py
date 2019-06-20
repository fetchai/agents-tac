#!/usr/bin/env python3
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
import argparse
import asyncio
import copy
import logging
import pprint
import random
import time
from enum import Enum
from typing import List, Optional, Set, Tuple

from oef.messages import CFP_TYPES, PROPOSE_TYPES
from oef.query import Query
from oef.schema import Description

from tac.agents.v1.core import NegotiationAgent
from tac.agents.v1.base.lock_manager import LockManager
from tac.platform.game import WorldState
from tac.helpers.misc import generate_transaction_id, build_query, get_goods_quantities_description, \
    TAC_SUPPLY_DATAMODEL_NAME, marginal_utility, TacError
from tac.platform.protocol import Transaction, TransactionConfirmation, Error, ErrorCode

if __name__ != "__main__":
    logger = logging.getLogger(__name__)
else:
    logger = logging.getLogger("tac.agents.baseline")


def parse_arguments():
    parser = argparse.ArgumentParser("baseline", description="Launch the baseline agent.")
    parser.add_argument("--name", default="baseline", help="Name of the agent.")
    parser.add_argument("--oef-addr", default="127.0.0.1", help="TCP/IP address of the OEF Agent")
    parser.add_argument("--oef-port", default=10000, help="TCP/IP port of the OEF Agent")
    # parser.add_argument("--gui", action="store_true", help="Show the GUI.")

    return parser.parse_args()


# these are the search IDs to be used to execute the search queries.
TAC_SELLERS_SEARCH_ID = 2
TAC_BUYERS_SEARCH_ID = 3
# these are default ids for the start of a message chain
STARTING_MESSAGE_REF = 0
STARTING_MESSAGE_ID = 1

DIALOGUE_LABEL = Tuple[str, int]  # (origin, dialogue_id)


class RegisterAs(Enum):
    SELLER = 'seller'
    BUYER = 'buyer'
    BOTH = 'both'


class SearchFor(Enum):
    SELLERS = 'sellers'
    BUYERS = 'buyers'
    BOTH = 'both'


class BaselineAgent(NegotiationAgent):
    """
    The baseline agent simply tries to improve its utility by selling good bundles at a price equal
    to their marginal utility and buying goods at a price plus fee equal or below their marginal utility.
    """

    def __init__(self, name: str, oef_addr: str, oef_port: int = 10000, register_as: str = RegisterAs.BOTH, search_for: str = SearchFor.BOTH, is_world_modeling: bool = False, pending_transaction_timeout: int = 30, **kwargs):
        super().__init__(name, oef_addr, oef_port, is_world_modeling, **kwargs)
        self._register_as = register_as
        self._search_for = search_for

        self.goods_supplied_description = None
        self.goods_demanded_description = None

        self._all_dialogues = set()  # type: Set[DIALOGUE_LABEL]
        self._dialogues_as_buyer = set()  # type: Set[DIALOGUE_LABEL]
        self._dialogues_as_seller = set()  # type: Set[DIALOGUE_LABEL]

        self.lock_manager = LockManager(name, pending_transaction_timeout=pending_transaction_timeout)
        self.lock_manager.start()

        self._stopped = False

    @property
    def is_registering_as_seller(self):
        return self._register_as == RegisterAs.SELLER or self._register_as == RegisterAs.BOTH

    @property
    def is_searching_for_sellers(self):
        return self._search_for == SearchFor.SELLER or self._search_for == SearchFor.BOTH

    @property
    def is_registering_as_buyer(self):
        return self._register_as == RegisterAs.BUYER or self._register_as == RegisterAs.BOTH

    @property
    def is_searching_for_buyers(self):
        return self._search_for == SearchFor.BUYER or self._search_for == SearchFor.BOTH

    def on_start(self) -> None:
        """
        Handle the 'start' event emitted by the controller.

        :return: None
        """
        logger.debug("[{}]: Received start event from the controller. Starting...".format(self.name))
        self._start_loop()

    def _start_loop(self) -> None:
        """
        Start loop:

        - Register to the OEF Service Directory
        - Search on OEF Service Directory

        :return: None
        """
        if self._stopped:
            logger.debug("[{}]: Not proceeding with the main loop, since the agent has stopped.".format(self.name))
            return

        if self.goods_demanded_description is not None:
            self.unregister_service(1, self.goods_demanded_description)
        if self.goods_supplied_description is not None:
            self.unregister_service(1, self.goods_supplied_description)

        time.sleep(0.5)
        self._register_services()
        time.sleep(0.5)
        self._search_services()

    def on_cancelled(self) -> None:
        """
        Handle the 'cancel' event emitted by the controller.

        :return: None
        """
        logger.debug("[{}]: Received cancellation from the controller. Stopping...".format(self.name))
        self._loop.call_soon_threadsafe(self.stop)
        self.lock_manager.stop()
        self._stopped = True

    def _register_services(self) -> None:
        """
        Register to the OEF Service Directory
            - as a seller, listing the goods supplied, or
            - as a buyer, listing the goods demanded, or
            - as both.

        :return: None
        """
        if self.is_registering_as_seller:
            logger.debug("[{}]: Updating service directory as seller with goods supplied.".format(self.name))
            goods_supplied_description = self._get_goods_description(is_supply=True)
            self.goods_supplied_description = goods_supplied_description
            self.register_service(STARTING_MESSAGE_REF, goods_supplied_description)
        if self.is_registering_as_buyer:
            logger.debug("[{}]: Updating service directory as buyer with goods demanded.".format(self.name))
            goods_demanded_description = self._get_goods_description(is_supply=False)
            self.goods_demanded_description = goods_demanded_description
            self.register_service(STARTING_MESSAGE_REF, goods_demanded_description)

    def _get_goods_description(self, is_supply: bool) -> Description:
        """
        Get the description of
            - the supplied goods (as a seller), or
            - the demanded goods (as a buyer).

        :param is_supply: Boolean indicating whether it is supply or demand.

        :return: the description (to advertise on the Service Directory).
        """

        desc = get_goods_quantities_description(self.game_configuration.good_pbks,
                                                self._get_goods_quantities(is_supply),
                                                is_supply=is_supply)
        return desc

    def _search_services(self) -> None:
        """
        Search on OEF Service Directory
            - for sellers and their supply, or
            - for buyers and their demand, or
            - for both.

        :return: None
        """
        if self.is_searching_for_sellers:
            query = self._build_query(is_searching_for_sellers=True)
            if query is None:
                logger.warning("[{}]: Not searching the OEF for sellers because the agent demands no goods.".format(self.name))
                return None
            else:
                logger.debug("[{}]: Searching for sellers which match the demand of the agent.".format(self.name))
                self.search_services(TAC_SELLERS_SEARCH_ID, query)
        if self.is_searching_for_buyers:
            query = self._build_query(is_searching_for_sellers=False)
            if query is None:
                logger.warning("[{}]: Not searching the OEF for buyers because the agent supplies no goods.".format(self.name))
                return None
            else:
                logger.debug("[{}]: Searching for buyers which match the supply of the agent.".format(self.name))
                self.search_services(TAC_BUYERS_SEARCH_ID, query)

    def _build_query(self, is_searching_for_sellers: bool) -> Optional[Query]:
        """
        Build the query to look for agents
            - which supply the agent's demanded goods (i.e. sellers), or
            - which demand the agent's supplied goods (i.e. buyers).

        :param is_searching_for_sellers: Boolean indicating whether the search is for sellers or buyers.

        :return: the Query, or None.
        """
        good_pbks = self._get_goods_pbks(is_supply=not is_searching_for_sellers)

        res = None if len(good_pbks) == 0 else build_query(good_pbks, is_searching_for_sellers)
        return res

    def on_search_results(self, search_id: int, agent_pbks: List[str]) -> None:
        """
        Handle the 'search_results' event:

        :param agent_pbks: a list of agent public keys matching the search query.

        :return: None
        """
        logger.debug("[{}]: on search result: {} {}".format(self.name, search_id, agent_pbks))
        if search_id == TAC_SELLERS_SEARCH_ID:
            self._on_search_result(agent_pbks, is_searching_for_sellers=True)
            return
        elif search_id == TAC_BUYERS_SEARCH_ID:
            self._on_search_result(agent_pbks, is_searching_for_sellers=False)
            return
        else:
            raise Exception("Unexpected search result received.")

    def _on_search_result(self, agent_pbks: List[str], is_searching_for_sellers: bool) -> None:
        """
        Callback of the search result for agents which
            - supply the goods the agent demands.
            - demand the goods the agent supplies.

        The actions are:
        - build a CFP query to identify if the agent still demands/supplies goods and which ones
        - send a CFP to every agent found matching the search query

        if there is no need for any good, do nothing.

        :param is_searching_for_sellers: Boolean indicating whether search is for sellers or buyers.
        :param agent_pbks: a list of agent public keys.

        :return: None
        """
        searched_for = 'sellers' if is_searching_for_sellers else 'buyers'
        role = 'buyer' if is_searching_for_sellers else 'seller'
        is_seller = False if is_searching_for_sellers else True
        logger.debug("[{}]: Found potential {}: {}".format(self.name, searched_for, agent_pbks))

        query = self._build_query(is_searching_for_sellers)
        if query is None:
            response = 'demanding' if is_searching_for_sellers else 'supplying'
            logger.debug("[{}]: No longer {} any goods...".format(self.name, response))

            self._start_loop()
            return
        for agent_pbk in agent_pbks:
            if agent_pbk == self.public_key: continue
            dialogue_id = random.randint(0, 2 ** 31)
            self._save_dialogue_id(agent_pbk, dialogue_id, is_seller)
            logger.debug("[{}]: send_cfp_as_{}: msg_id={}, dialogue_id={}, destination={}, target={}, query={}"
                         .format(self.name, role, STARTING_MESSAGE_ID, dialogue_id, agent_pbk, STARTING_MESSAGE_REF, query))
            self.send_cfp(STARTING_MESSAGE_ID, dialogue_id, agent_pbk, STARTING_MESSAGE_REF, query)

    def on_cfp(self, msg_id: int, dialogue_id: int, origin: str, target: int, query: CFP_TYPES) -> None:
        """
        Dispatch the CFP message to the correct handler.

        :param msg_id: the message id
        :param dialogue_id: the dialogue id
        :param origin: the public key of the message sender.
        :param target: the targeted message id to which this message is a response.
        :param query: the query associated with the cfp.

        :return: None
        """
        logger.debug("[{}]: on_cfp: msg_id={}, dialogue_id={}, origin={}, target={}, query={}"
                     .format(self.name, msg_id, dialogue_id, origin, target, query))

        if origin in self.game_configuration.agent_pbks:
            # if the cfp is from a buyer, then the buyer query references the seller/supply model (i.e. the buyer is searching for sellers)
            is_seller = query.model.name == TAC_SUPPLY_DATAMODEL_NAME
            self._on_cfp(msg_id, dialogue_id, origin, target, query, is_seller)
        else:
            raise TacError("Message received from unknown agent.")

    def _on_cfp(self, msg_id: int, dialogue_id: int, origin: str, target: int, query: CFP_TYPES, is_seller: bool) -> None:
        """
        On CFP handler.

        - If the current holdings do not satisfy the CFP query, answer with a Decline
        - Otherwise, make a proposal.

        :param msg_id: the message id
        :param dialogue_id: the dialogue id
        :param origin: the public key of the message sender.
        :param target: the targeted message id to which this message is a response.
        :param query: the query associated with the cfp.
        :param is_seller: boolean indicating the role of the agent

        :return: None
        """
        self._save_dialogue_id(origin, dialogue_id, is_seller)
        goods_description = self._get_goods_description(is_supply=is_seller)
        new_msg_id = msg_id + 1
        if not query.check(goods_description):
            logger.debug("[{}]: Current holdings do not satisfy CFP query.".format(self.name))
            logger.debug("[{}]: sending to {} a Decline{}".format(self.name, origin,
                                                                  pprint.pformat({
                                                                      "msg_id": new_msg_id,
                                                                      "dialogue_id": dialogue_id,
                                                                      "origin": origin,
                                                                      "target": msg_id
                                                                  })))
            self.send_decline(new_msg_id, dialogue_id, origin, msg_id)
        else:
            proposals = [random.choice(self._get_proposals(query, is_seller))]
            self._store_proposals(proposals, new_msg_id, dialogue_id, origin, is_seller)
            logger.debug("[{}]: sending to {} a Propose{}".format(self.name, origin,
                                                                  pprint.pformat({
                                                                      "msg_id": new_msg_id,
                                                                      "dialogue_id": dialogue_id,
                                                                      "origin": origin,
                                                                      "target": msg_id,
                                                                      "propose": proposals[0].values  # TODO fix if more than one proposal!
                                                                  })))
            self.send_propose(new_msg_id, dialogue_id, origin, msg_id, proposals)

    def _store_proposals(self, proposals: List[Description], new_msg_id: int, dialogue_id: int, origin: str, is_seller: bool) -> None:
        """
        Store proposals as pending transactions.

        :param new_msg_id: the new message id
        :param dialogue_id: the dialogue id
        :param origin: the public key of the message sender.
        :param is_seller: Boolean indicating the role of the agent

        :return: None
        """
        for proposal in proposals:
            proposal_id = new_msg_id  # TODO fix if more than one proposal!
            transaction_id = generate_transaction_id(self.public_key, origin, dialogue_id, is_seller)  # TODO fix if more than one proposal!
            transaction = Transaction.from_proposal(proposal=proposal,
                                                    transaction_id=transaction_id,
                                                    is_buyer=not is_seller,
                                                    counterparty=origin,
                                                    sender=self.public_key,
                                                    crypto=self.crypto)
            self.lock_manager.add_pending_proposal(dialogue_id, origin, proposal_id, transaction)

    def on_propose(self, msg_id: int, dialogue_id: int, origin: str, target: int, proposals: PROPOSE_TYPES) -> None:
        """
        On propose dispatcher.

        :param msg_id: the message id
        :param dialogue_id: the dialogue id
        :param origin: the public key of the message sender.
        :param target: the targeted message id to which this message is a response.
        :param proposals: the proposals associated with the message.

        :return: None
        """
        logger.debug("[{}]: on_propose: msg_id={}, dialogue_id={}, origin={}, target={}, proposals={}"
                     .format(self.name, msg_id, dialogue_id, origin, target, proposals))

        if origin in self.game_configuration.agent_pbks:
            is_seller = self._is_seller(dialogue_id, origin)
            self._on_propose(msg_id, dialogue_id, origin, target, proposals, is_seller)
        else:
            raise TacError("Message received from unknown agent.")

    def _on_propose(self, msg_id: int, dialogue_id: int, origin: str, target: int, proposals: PROPOSE_TYPES, is_seller: bool) -> None:
        """
        On Propose handler.

        1. parse the propose object
        2. compute the score of the propose.
            - if the proposed transaction increases the score,
              send an accept and lock the state waiting for the matched accept.
            - otherwise, decline the propose.

        :param msg_id: the message id
        :param dialogue_id: the dialogue id
        :param origin: the public key of the message sender.
        :param target: the targeted message id to which this message is a response.
        :param proposals: the proposals associated with the message.
        :param is_seller: boolean indicating the role of the agent.

        :return: None
        """
        role = 'seller' if is_seller else 'buyer'
        logger.debug("[{}]: on propose as {}.".format(self.name, role))
        proposal = proposals[0]
        transaction_id = generate_transaction_id(self.public_key, origin, dialogue_id, is_seller)
        transaction = Transaction.from_proposal(proposal,
                                                transaction_id,
                                                is_buyer=not is_seller,
                                                counterparty=origin,
                                                sender=self.public_key,
                                                crypto=self.crypto)
        if self._is_profitable_transaction(transaction, is_seller):
            logger.debug("[{}]: Accepting propose (as {}).".format(self.name, role))
            self._accept_propose(msg_id, dialogue_id, origin, target, proposals, is_seller)
        # TODO counter-propose
        else:
            logger.debug("[{}]: Declining propose (as {})".format(self.name, role))
            self.send_decline(msg_id + 1, dialogue_id, origin, msg_id)
            self._delete_dialogue_id(origin, dialogue_id)

    def _accept_propose(self, msg_id: int, dialogue_id: int, origin: str, target: int, proposals: PROPOSE_TYPES, is_seller: bool) -> None:
        """
        Accept a propose.

        :param msg_id: the message id
        :param dialogue_id: the dialogue id
        :param origin: the public key of the message sender.
        :param target: the targeted message id to which this message is a response.
        :param proposals: the proposals associated with the message.
        :param is_seller: boolean indicating the role of the agent.

        :return: None
        """
        role = 'seller' if is_seller else 'buyer'
        logger.debug("[{}]: accept propose as {}".format(self.name, role))

        # compute the transaction request from the propose.
        proposal = proposals[0]
        transaction_id = generate_transaction_id(self.public_key, origin, dialogue_id, is_seller)
        transaction = Transaction.from_proposal(proposal=proposal,
                                                transaction_id=transaction_id,
                                                is_buyer=not is_seller,
                                                counterparty=origin,
                                                sender=self.public_key,
                                                crypto=self.crypto)

        logger.debug("[{}]: Locking the current state (as {}).".format(self.name, role))
        self.lock_manager.add_lock(transaction, as_seller=is_seller)

        # add to pending acceptances
        new_msg_id = msg_id + 1
        self.lock_manager.add_pending_acceptances(dialogue_id, origin, new_msg_id, transaction)

        self.send_accept(new_msg_id, dialogue_id, origin, msg_id)

    def on_decline(self, msg_id: int, dialogue_id: int, origin: str, target: int) -> None:
        """
        On Decline handler.

        :param msg_id: the message id
        :param dialogue_id: the dialogue id
        :param origin: the public key of the message sender.
        :param target: the targeted message id to which this message is a response.

        :return: None
        """
        logger.debug("[{}]: on_decline: msg_id={}, dialogue_id={}, origin={}, target={}"
                     .format(self.name, msg_id, dialogue_id, origin, target))

        if origin in self.game_configuration.agent_pbks:
            dialogue_label = (dialogue_id, origin)

            if self.is_world_modeling:
                if dialogue_label in self.lock_manager.pending_tx_proposals and target in self.lock_manager.pending_tx_proposals[dialogue_label]:
                    transaction = self.lock_manager.pop_pending_proposal(dialogue_id, origin, target)
                    self._world_state.update_on_decline(transaction)

            is_seller = self._is_seller(dialogue_id, origin)
            transaction_id = generate_transaction_id(self.public_key, origin, dialogue_id, is_seller)
            if transaction_id in self.lock_manager.locks:
                self.lock_manager.pop_lock(transaction_id)

            self._delete_dialogue_id(origin, dialogue_id)
            self._start_loop()
        else:
            raise TacError("Message received from unknown agent.")

    def on_accept(self, msg_id: int, dialogue_id: int, origin: str, target: int) -> None:
        """
        On Accept dispatcher.

        :param msg_id: the message id
        :param dialogue_id: the dialogue id
        :param origin: the public key of the message sender.
        :param target: the targeted message id to which this message is a response.

        :return: None
        """
        logger.debug("[{}]: on_accept: msg_id={}, dialogue_id={}, origin={}, target={}"
                     .format(self.name, msg_id, dialogue_id, origin, target))

        if origin in self.game_configuration.agent_pbks:
            dialogue_label = (origin, dialogue_id)  # type: DIALOGUE_LABEL
            acceptance_id = target
            if dialogue_label in self.lock_manager.pending_tx_acceptances \
                    and acceptance_id in self.lock_manager.pending_tx_acceptances[dialogue_label]:
                self._on_match_accept(msg_id, dialogue_id, origin, target)
            else:
                self._on_accept(msg_id, dialogue_id, origin, target)
        else:
            raise TacError("Message received from unknown agent.")

    def _on_accept(self, msg_id: int, dialogue_id: int, origin: str, target: int) -> None:
        """
        On Accept handler.

        :param msg_id: the message id
        :param dialogue_id: the dialogue id
        :param origin: the public key of the message sender.
        :param target: the targeted message id to which this message is a response.

        :return: None
        """
        is_seller = self._is_seller(dialogue_id, origin)
        self._on_accept_as_role(msg_id, dialogue_id, origin, target, is_seller)

    def _on_accept_as_role(self, msg_id: int, dialogue_id: int, origin: str, target: int, is_seller: bool):
        """
        Handles accept of specified role.

        :param msg_id: the message id
        :param dialogue_id: the dialogue id
        :param origin: the public key of the message sender.
        :param target: the targeted message id to which this message is a response.
        :param is_seller: Boolean indicating the role of the agent.

        :return: None
        """
        role = 'seller' if is_seller else 'buyer'
        transaction = self.lock_manager.pop_pending_proposal(dialogue_id, origin, target)
        if self._is_profitable_transaction(transaction, is_seller):
            if self.is_world_modeling:
                self._world_state.update_on_accept(transaction)
            logger.debug("[{}]: Locking the current state (as {}).".format(self.name, role))
            self.lock_manager.add_lock(transaction, as_seller=is_seller)
            self.submit_transaction_to_controller(transaction)
            self.send_accept(msg_id + 1, dialogue_id, origin, msg_id)
        else:
            logger.debug("[{}]: Decline the accept (as {}).".format(self.name, role))
            self.send_decline(msg_id + 1, dialogue_id, origin, msg_id)

    def _on_match_accept(self, msg_id: int, dialogue_id: int, origin: str, target: int):
        """
        Handles match accept.

        :param msg_id: the message id
        :param dialogue_id: the dialogue id
        :param origin: the public key of the message sender.
        :param target: the targeted message id to which this message is a response.

        :return: None
        """
        # TODO implement at SDK level and proper error handling
        logger.debug("[{}]: on match accept".format(self.name))

        transaction = self.lock_manager.pop_pending_acceptances(dialogue_id, origin, target)
        self.submit_transaction_to_controller(transaction)

    def on_transaction_confirmed(self, tx_confirmation: TransactionConfirmation) -> None:
        """
        Handles 'on transaction confirmed' event emitted by the controller.

        :param tx_confirmation: the transaction confirmation

        :return: None
        """
        logger.debug("[{}]: on transaction confirmed: {}".format(self.name, tx_confirmation.transaction_id))
        transaction = self.lock_manager.pop_lock(tx_confirmation.transaction_id)
        self._agent_state.update(transaction, self.game_configuration.tx_fee)

        self._start_loop()

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
            if transaction_id in self.lock_manager.locks:
                self.lock_manager.pop_lock(transaction_id)
            else:
                logger.warning("[{}]: Received error on unknown transaction id: {}".format(self.name, transaction_id))

    def _save_dialogue_id(self, dialogue_starter_pbk: str, dialogue_id: int, is_seller: bool):
        """
        Saves the dialogue id.

        :param dialogue_starter_pbk: the pbk of the agent which started the dialogue
        :param dialogue_id: the dialogue id
        :param is_seller: boolean indicating the agent role

        :return: None
        """
        dialogue_label = (dialogue_starter_pbk, dialogue_id)
        assert dialogue_label not in self._all_dialogues
        if is_seller:
            assert dialogue_label not in self._dialogues_as_seller
            self._dialogues_as_seller.add(dialogue_label)
        else:
            assert dialogue_label not in self._dialogues_as_buyer
            self._dialogues_as_buyer.add(dialogue_label)
        logger.debug("[{}]: saving dialogue {}".format(self.name, dialogue_label))
        self._all_dialogues.add(dialogue_label)

    def _delete_dialogue_id(self, origin: str, dialogue_id: int):
        """
        Deletes the dialogue id.

        :param origin: the public key of the message sender.
        :param dialogue_id: the dialogue id

        :return: None
        """
        dialogue_label = (origin, dialogue_id)
        logger.debug("[{}]: deleting dialogue {}".format(self.name, dialogue_label))
        assert dialogue_label in self._all_dialogues
        assert dialogue_label in self._dialogues_as_buyer or dialogue_label in self._dialogues_as_seller

        self._all_dialogues.remove(dialogue_label)
        if dialogue_label in self._dialogues_as_buyer:
            self._dialogues_as_buyer.remove(dialogue_label)
        elif dialogue_label in self._dialogues_as_seller:
            self._dialogues_as_seller.remove(dialogue_label)
        else:
            assert False

    def _is_profitable_transaction(self, transaction: Transaction, is_seller: bool) -> bool:
        """
        Is a profitable transaction?
        - apply all the locks for role.
        - check if the transaction is consistent with the locks (enough money/holdings)
        - check that we gain score.

        :param transaction: the transaction
        :param is_seller: Boolean indicating the role of the agent.

        :return: True if the transaction is good (as stated above), False otherwise.
        """

        role = 'seller' if is_seller else 'buyer'
        state_after_locks = self._state_after_locks(is_seller)

        if not state_after_locks.check_transaction_is_consistent(transaction, self.game_configuration.tx_fee):
            logger.debug("[{}]: the proposed transaction is not consistent with the state after locks.".format(self.name))
            return False

        proposal_delta_score = state_after_locks.get_score_diff_from_transaction(transaction, self.game_configuration.tx_fee)

        result = proposal_delta_score >= 0
        logger.debug("[{}]: is good proposal for {}? {}: tx_id={}, "
                     "delta_score={}, amount={}"
                     .format(self.name, role, result, transaction.transaction_id,
                             proposal_delta_score, transaction.amount))
        return result

    def _state_after_locks(self, is_seller: bool):
        """
        Apply all the locks to the current state of the agent. That is, assuming all
        the locked transactions will be successful.

        :param is_seller: Boolean indicating the role of the agent.

        :return: the agent state with the locks applied to current state
        """
        transactions = list(self.lock_manager.locks_as_seller.values()) if is_seller \
            else list(self.lock_manager.locks_as_buyer.values())
        state_after_locks = self._agent_state.apply(transactions, self.game_configuration.tx_fee)
        return state_after_locks

    def _is_seller(self, dialogue_id: int, origin: str) -> bool:
        """
        Check if the agent has the seller role.

        :param dialogue_id: the dialogue id
        :param origin: the public key of the message sender.

        :return: boolean indicating whether the agent is a seller or buyer.
        """
        is_buyer = (origin, dialogue_id) in self._dialogues_as_buyer
        is_seller = (origin, dialogue_id) in self._dialogues_as_seller
        if not is_buyer == (not is_seller):
            raise TacError("This dialogue is not specified.")
        return is_seller

    ###
    # Strategy wrappers
    ###

    def _get_goods_quantities(self, is_supply: bool) -> List[int]:
        """
        Wraps the function which determines supplied and demanded good quantities.

        :param is_supply: Boolean indicating whether it is referencing the supplied or demanded quantities.

        :return: the vector of good quantities offered/requested.
        """
        state_after_locks = self._state_after_locks(is_seller=is_supply)
        quantities = BaselineStrategy.supplied_good_quantities(state_after_locks.current_holdings) if is_supply else BaselineStrategy.demanded_good_quantities(state_after_locks.current_holdings)
        return quantities

    def _get_goods_pbks(self, is_supply: bool) -> Set[str]:
        """
        Wraps the function which determines supplied and demanded good pbks.

        :param is_supply: Boolean indicating whether it is referencing the supplied or demanded pbks.

        :return: a list of good pbks
        """
        state_after_locks = self._state_after_locks(is_seller=is_supply)
        pbks = BaselineStrategy.supplied_good_pbks(self.game_configuration.good_pbks, state_after_locks.current_holdings) if is_supply else BaselineStrategy.demanded_good_pbks(self.game_configuration.good_pbks, state_after_locks.current_holdings)
        return pbks

    def _get_proposals(self, query: CFP_TYPES, is_seller: bool) -> List[Description]:
        """
        Wraps the function which generates proposals from a seller or buyer.

        If there are locks as seller, it applies them.

        :param query: the query associated with the cfp.
        :param is_seller: Boolean indicating the role of the agent.

        :return: a list of descriptions
        """
        state_after_locks = self._state_after_locks(is_seller=is_seller)
        candidate_proposals = BaselineStrategy.get_proposals(self.game_configuration.good_pbks, state_after_locks.current_holdings, state_after_locks.utility_params, self.game_configuration.tx_fee, is_seller, self.is_world_modeling, self._world_state)
        proposals = []
        for proposal in candidate_proposals:
            if not query.check(proposal): continue
            proposals.append(proposal)
        if proposals == []:
            proposals.append(candidate_proposals[0])  # TODO remove this
        return proposals


class BaselineStrategy:
    def supplied_good_quantities(current_holdings: List[int]) -> List[int]:
        """
        Generates list of quantities which are supplied.

        :param current_holdings: a list of current good holdings
        :return: a list of quantities
        """
        return [quantity - 1 for quantity in current_holdings]

    def supplied_good_pbks(good_pbks: List[str], current_holdings: List[int]) -> Set[str]:
        """
        Generates set of good pbks which are supplied.

        :param good_pbks: a list of good pbks
        :param current_holdings: a list of current good holdings
        :return: a set of pbks
        """
        return {good_pbk for good_pbk, quantity in zip(good_pbks, current_holdings) if quantity > 1}

    def demanded_good_quantities(current_holdings: List[int]) -> List[int]:
        """
        Generates list of quantities which are demanded.

        :param current_holdings: a list of current good holdings
        :return: a list of quantities
        """
        return [1 for _ in current_holdings]

    def demanded_good_pbks(good_pbks: List[str], current_holdings: List[int]) -> Set[str]:
        """
        Generates set of good pbks which are demanded.

        :param good_pbks: a list of good pbks
        :param current_holdings: a list of current good holdings
        :return: a set of pbks
        """
        return {good_pbk for good_pbk, quantity in zip(good_pbks, current_holdings)}

    def get_proposals(good_pbks: List[str], current_holdings: List[int], utility_params: List[int], tx_fee: float, is_seller: bool, is_world_modeling: bool, world_state: WorldState) -> List[Description]:
        """
        Generates proposals from the seller/buyer.

        :param good_pbks: a list of good pbks
        :param current_holdings: a list of current good holdings
        :param utility_params: a list of utility params
        :param tx_fee: the transaction fee
        :param is_seller: Boolean indicating the role of the agent

        :return: a list of proposals in Description form
        """
        quantities = BaselineStrategy.supplied_good_quantities(current_holdings) if is_seller else BaselineStrategy.demanded_good_quantities(current_holdings)
        proposals = []
        zeroslist = [0] * len(quantities)
        rounding_adjustment = 0.01
        for good_id, good_pbk in zip(range(len(quantities)), good_pbks):
            if is_seller and quantities[good_id] == 0: continue
            lis = copy.deepcopy(zeroslist)
            lis[good_id] = 1
            desc = get_goods_quantities_description(good_pbks, lis, is_supply=is_seller)
            delta_holdings = [i * -1 for i in lis] if is_seller else lis
            switch = -1 if is_seller else 1
            marginal_utility_from_single_good = marginal_utility(utility_params, current_holdings, delta_holdings) * switch
            share_of_tx_fee = round(tx_fee / 2.0, 2)
            if is_world_modeling:
                desc.values["price"] = world_state.expected_price(good_pbk, round(marginal_utility_from_single_good, 2), is_seller, share_of_tx_fee)
            else:
                if is_seller:
                    desc.values["price"] = round(marginal_utility_from_single_good, 2) + share_of_tx_fee + rounding_adjustment
                else:
                    desc.values["price"] = round(marginal_utility_from_single_good, 2) - share_of_tx_fee - rounding_adjustment
            proposals.append(desc)
        return proposals


def main():
    args = parse_arguments()
    agent = BaselineAgent(name=args.name, oef_addr=args.oef_addr, oef_port=args.oef_port,
                          loop=asyncio.get_event_loop())

    agent.connect()
    agent.search_for_tac()

    logger.debug("[{}]: running myself...".format(agent.name))
    agent.run()


if __name__ == '__main__':
    main()

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
from collections import defaultdict
from typing import List, Optional, Dict, Set, Tuple

from oef.messages import CFP_TYPES, PROPOSE_TYPES
from oef.query import Query
from oef.schema import Description

from tac.core import NegotiationAgent
from tac.helpers.misc import generate_transaction_id, build_query, get_goods_quantities_description, \
    from_good_attribute_name_to_good_id, TAC_SELLER_DATAMODEL_NAME, marginal_utility
from tac.protocol import GameData, Transaction, TransactionConfirmation, Error, ErrorCode

logger = logging.getLogger(__name__)


def parse_arguments():
    parser = argparse.ArgumentParser("baseline", description="Launch the baseline agent.")
    parser.add_argument("--public-key", default="baseline", help="Public key of the agent.")
    parser.add_argument("--oef-addr", default="127.0.0.1", help="TCP/IP address of the OEF Agent")
    parser.add_argument("--oef-port", default=3333, help="TCP/IP port of the OEF Agent")
    # parser.add_argument("--gui", action="store_true", help="Show the GUI.")

    return parser.parse_args()


# these are the search IDs to be used to execute the search queries.
TAC_SELLER_SEARCH_ID = 2
TAC_BUYER_SEARCH_ID = 3
# these are default ids for the start of a message chain
STARTING_MESSAGE_REF = 0
STARTING_MESSAGE_ID = 1

DIALOGUE_LABEL = Tuple[str, int]  # (origin, dialogue_id)
MESSAGE_ID = int


class BaselineAgent(NegotiationAgent):
    """
    The baseline agent simply tries to improve its utility by selling good bundles at a price equal
    to their marginal utility and buying goods at a price plus fee equal or below their marginal utility.
    """

    def __init__(self, public_key: str, oef_addr: str, oef_port: int = 3333, service_registration_strategy: str = 'both', **kwargs):
        super().__init__(public_key, oef_addr, oef_port, **kwargs)
        self._service_registration_strategy = service_registration_strategy

        self.tac_search_id = set()

        self._all_dialogues = set()  # type: Set[DIALOGUE_LABEL]
        self._dialogues_as_buyer = set()  # type: Set[DIALOGUE_LABEL]
        self._dialogues_as_seller = set()  # type: Set[DIALOGUE_LABEL]

        self._pending_proposals = defaultdict(lambda: {})  # type: Dict[DIALOGUE_LABEL, Dict[MESSAGE_ID, Transaction]]
        self._pending_acceptances = defaultdict(lambda: {})  # type: Dict[DIALOGUE_LABEL, Dict[MESSAGE_ID, Transaction]]

        self._locks = {}  # type: Dict[str, Transaction]
        self._locks_as_buyer = {}  # type: Dict[str, Transaction]
        self._locks_as_seller = {}  # type: Dict[str, Transaction]

        self._stopped = False

    def on_start(self, game_data: GameData) -> None:
        """
        Handle the 'start' event (baseline agent):

        - Register to the OEF as a seller of the supplied goods.
        - Register to the OEF as a buyer of the demanded goods.
        - Search for the goods offered by other agents, and eventually start a negotiation as the buyer.
        - Search for the goods requested by other agents, and eventually start a negotiation as the seller.

        :param game_data: the game data
        :return: None
        """
        self._start_loop()

    def _start_loop(self) -> None:
        """
        Start loop.
        :return: None
        """
        if self._stopped:
            logger.debug("Not proceeding with the main loop, since the agent has stopped.")
            return

        logger.debug("[{}]: Updating service directory and searching for sellers.".format(self.public_key))
        if self._service_registration_strategy == 'supply' or self._service_registration_strategy == 'both':
            self._register_as_seller()
        if self._service_registration_strategy == 'demand' or self._service_registration_strategy == 'both':
            self._register_as_buyer()
        time.sleep(1.0)
        if self._service_registration_strategy == 'supply' or self._service_registration_strategy == 'both':
            self._search_for_sellers()
        if self._service_registration_strategy == 'demand' or self._service_registration_strategy == 'both':
            self._search_for_buyers()

    def on_cancelled(self):
        logger.debug("[{}]: Received cancellation from the controller. Stopping...".format(self.public_key))
        self._loop.call_soon_threadsafe(self._task.cancel)
        self._stopped = True

    def _register_as_seller(self) -> None:
        """
        Register to the Service Directory as a seller, listing the goods supplied.

        :return: None
        """
        logger.debug("[{}]: Register as seller.".format(self.public_key))
        goods_supplied_description = self._get_goods_supplied_description()
        # TODO: define 0 explicit via a constant
        self.register_service(0, goods_supplied_description)

    def _register_as_buyer(self) -> None:
        """
        Register to the Service Directory as a buyer, listing the goods demanded.

        :return: None
        """
        logger.debug("[{}]: Register as buyer.".format(self.public_key))
        goods_demanded_description = self._get_goods_demanded_description()
        self.register_service(0, goods_demanded_description)

    def _get_goods_supplied_description(self) -> Description:
        """
        Get the description of the supplied goods.

        :return: the description (to advertise on the Service Directory).
        """
        desc = get_goods_quantities_description(self._get_supplied_goods_quantities(), True)
        return desc

    def _get_goods_demanded_description(self) -> Description:
        """
        Get the description of the demanded goods.

        :return: the description (to advertise on the Service Directory).
        """
        desc = get_goods_quantities_description(self._get_demanded_goods_quantities(), False)
        return desc

    def _search_for_sellers(self) -> None:
        """
        Search on OEF core for sellers and their supply.

        :return: None
        """
        query = self._build_sellers_query()
        if query is None:
            logger.warning("[{}]: Not sending the query to the OEF because the agent demands no goods.".format(self.public_key))
            return None
        else:
            logger.debug("[{}]: Search for sellers.".format(self.public_key))
            self.search_services(TAC_SELLER_SEARCH_ID, query)

    def _search_for_buyers(self) -> None:
        """
        Search on OEF core for buyers and their demand.

        :return: None
        """
        query = self._build_buyers_query()
        if query is None:
            logger.warning("[{}]: Not sending the query to the OEF because the agent supplies no goods.".format(self.public_key))
            return None
        else:
            logger.debug("[{}]: Search for buyers.".format(self.public_key))
            self.search_services(TAC_BUYER_SEARCH_ID, query)

    def _build_sellers_query(self) -> Optional[Query]:
        """
        Build the query to look for agents which supply the agent's demanded goods.

        :return the Query, or None.
        """
        demanded_goods_ids = self._get_demanded_goods_ids()

        if len(demanded_goods_ids) == 0:
            return None
        else:
            return build_query(demanded_goods_ids, True, self._game_configuration.nb_goods)

    def _build_buyers_query(self) -> Optional[Query]:
        """
        Build the query to look for agents which demand the agent's supplied goods.

        :return the Query, or None.
        """
        supplied_goods_ids = self._get_supplied_goods_ids()

        if len(supplied_goods_ids) == 0:
            return None
        else:
            return build_query(supplied_goods_ids, False, self._game_configuration.nb_goods)

    def on_search_results(self, search_id: int, agents: List[str]) -> None:
        """
        Handle the 'search_results' event (baseline agent):

        :return: None
        """
        logger.debug("[{}]: on search result: {} {}".format(self.public_key, search_id, agents))
        if search_id == TAC_SELLER_SEARCH_ID:
            self._on_sellers_search_result(agents)
            return
        elif search_id == TAC_BUYER_SEARCH_ID:
            self._on_buyers_search_result(agents)
            return
        else:
            raise Exception("Shouldn't be here.")

    def _on_sellers_search_result(self, sellers: List[str]) -> None:
        """
        Callback of the search result for agents which sell the goods the agent demands.

        The actions are:
        - build a CFP query to identify if any more goods are demanded and which ones
        - send a CFP to every agent found

        if there is no need for any good, do nothing.

        :param: sellers: a list of agent public keys.

        :return: None
        """

        logger.debug("[{}]: Found potential sellers: {}".format(self.public_key, sellers))

        query = self._build_sellers_query()
        if query is None:
            logger.debug("[{}]: No longer demanding any goods...".format(self.public_key))
            # TODO: could restart loop here
            return
        for seller in sellers:
            if seller == self.public_key: continue
            dialogue_id = random.randint(0, 2 ** 31)
            logger.debug("[{}]: send_cfp_as_buyer: msg_id={}, dialogue_id={}, destination={}, target={}, query={}"
                         .format(self.public_key, STARTING_MESSAGE_ID, dialogue_id, seller, STARTING_MESSAGE_REF, query))
            self.send_cfp(STARTING_MESSAGE_ID, dialogue_id, seller, STARTING_MESSAGE_REF, query)
            self._save_dialogue_id_as_buyer(seller, dialogue_id)

    def _on_buyers_search_result(self, buyers: List[str]) -> None:
        """
        Callback of the search result for agents which buy the goods the agent supplies.

        The actions are:
        - build a CFP query to identify if any more goods are supplied and which ones
        - send a CFP to every agent found
        if there is no need for any good, do nothing.

        :param: buyers: a list of agent public keys.

        :return: None
        """

        logger.debug("[{}]: Found potential buyers: {}".format(self.public_key, buyers))

        query = self._build_buyers_query()
        if query is None:
            logger.debug("[{}]: No longer supplying any goods...".format(self.public_key))
            return
        for buyer in buyers:
            if buyer == self.public_key: continue
            dialogue_id = random.randint(0, 2 ** 31)
            logger.debug("[{}]: send_cfp_as_seller: msg_id={}, dialogue_id={}, destination={}, target={}, query={}"
                         .format(self.public_key, STARTING_MESSAGE_ID, dialogue_id, buyer, STARTING_MESSAGE_REF, query))
            self.send_cfp(STARTING_MESSAGE_ID, dialogue_id, buyer, STARTING_MESSAGE_REF, query)
            self._save_dialogue_id_as_seller(buyer, dialogue_id)

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
                     .format(self.public_key, msg_id, dialogue_id, origin, target, query))

        is_cfp_from_buyer = query.model.name == TAC_SELLER_DATAMODEL_NAME
        if is_cfp_from_buyer:
            self._on_cfp_as_seller(msg_id, dialogue_id, origin, target, query)
        else:
            self._on_cfp_as_buyer(msg_id, dialogue_id, origin, target, query)

    def _on_cfp_as_seller(self, msg_id: int, dialogue_id: int, origin: str, target: int, query: CFP_TYPES) -> None:
        """
        On CFP handler for seller.

        - If the current holdings do not satisfy the CFP query, answer with a Decline
        - Otherwise, make a proposal.

        :param msg_id: the message id
        :param dialogue_id: the dialogue id
        :param origin: the public key of the message sender.
        :param target: the targeted message id to which this message is a response.
        :param query: the query associated with the cfp.

        :return: None
        """
        self._save_dialogue_id_as_seller(origin, dialogue_id)
        goods_supplied_description = self._get_goods_supplied_description()
        new_msg_id = msg_id + 1
        if not query.check(goods_supplied_description):
            logger.debug("[{}]: Current holdings do not satisfy CFP query.".format(self.public_key))
            logger.debug("[{}]: sending to {} a Decline{}".format(self.public_key, origin,
                                                                  pprint.pformat({
                                                                      "msg_id": new_msg_id,
                                                                      "dialogue_id": dialogue_id,
                                                                      "origin": origin,
                                                                      "target": msg_id
                                                                  })))
            self.send_decline(new_msg_id, dialogue_id, origin, msg_id)
        else:
            proposals = [random.choice(self._get_seller_proposals())]  # ToDo check proposal is consistent with query. (e.g. select the subset of proposals which match the query)
            # store the proposed transaction in the pool of pending proposals.
            dialogue_label = (origin, dialogue_id)
            for proposal in proposals:
                proposal_id = new_msg_id  # TODO fix if more than one proposal!
                transaction_id = generate_transaction_id(origin, self.public_key, dialogue_id)  # TODO fix if more than one proposal!
                transaction = self._from_proposal_to_transaction(proposal=proposal,
                                                                 transaction_id=transaction_id,
                                                                 is_buyer=False,
                                                                 counterparty=origin)
                self._pending_proposals[dialogue_label][proposal_id] = transaction
            logger.debug("[{}]: sending to {} a Propose{}".format(self.public_key, origin,
                                                                  pprint.pformat({
                                                                      "msg_id": new_msg_id,
                                                                      "dialogue_id": dialogue_id,
                                                                      "origin": origin,
                                                                      "target": msg_id,
                                                                      "propose": proposals[0].values  # TODO fix if more than one proposal!
                                                                  })))
            self.send_propose(new_msg_id, dialogue_id, origin, msg_id, proposals)

    def _on_cfp_as_buyer(self, msg_id: int, dialogue_id: int, origin: str, target: int, query: CFP_TYPES) -> None:
        """
        On CFP handler for buyer.

        - If the current demand does not satisfy the CFP query, answer with a Decline
        - Otherwise, make a proposal.

        :param msg_id: the message id
        :param dialogue_id: the dialogue id
        :param origin: the public key of the message sender.
        :param target: the targeted message id to which this message is a response.
        :param query: the query associated with the cfp.

        :return: None
        """
        self._save_dialogue_id_as_buyer(origin, dialogue_id)
        goods_demanded_description = self._get_goods_demanded_description()
        new_msg_id = msg_id + 1
        if not query.check(goods_demanded_description):
            logger.debug("[{}]: Current holdings do not satisfy CFP query.".format(self.public_key))
            logger.debug("[{}]: sending to {} a Decline{}".format(self.public_key, origin,
                                                                  pprint.pformat({
                                                                      "msg_id": new_msg_id,
                                                                      "dialogue_id": dialogue_id,
                                                                      "origin": origin,
                                                                      "target": msg_id
                                                                  })))
            self.send_decline(new_msg_id, dialogue_id, origin, msg_id)
        else:
            proposals = [random.choice(self._get_buyer_proposals())]  # ToDo use all! # ToDo check proposal is consistent with query.  (e.g. select the subset of proposals which match the query)
            dialogue_label = (origin, dialogue_id)
            for proposal in proposals:
                proposal_id = new_msg_id  # TODO fix if more than one proposal!
                transaction_id = generate_transaction_id(origin, self.public_key, dialogue_id)  # TODO fix if more than one proposal!
                transaction = self._from_proposal_to_transaction(proposal=proposal,
                                                                 transaction_id=transaction_id,
                                                                 is_buyer=True,
                                                                 counterparty=origin)
                self._pending_proposals[dialogue_label][proposal_id] = transaction
            logger.debug("[{}]: sending to {} a Propose{}".format(self.public_key, origin,
                                                                  pprint.pformat({
                                                                      "msg_id": new_msg_id,
                                                                      "dialogue_id": dialogue_id,
                                                                      "origin": origin,
                                                                      "target": msg_id,
                                                                      "propose": proposals[0].values
                                                                  })))
            self.send_propose(new_msg_id, dialogue_id, origin, msg_id, proposals)

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
                     .format(self.public_key, msg_id, dialogue_id, origin, target, proposals))

        is_buyer = (origin, dialogue_id) in self._dialogues_as_buyer
        is_seller = (origin, dialogue_id) in self._dialogues_as_seller
        if is_buyer:
            self._on_propose_as_buyer(msg_id, dialogue_id, origin, target, proposals)
        elif is_seller:
            self._on_propose_as_seller(msg_id, dialogue_id, origin, target, proposals)
        else:
            raise Exception("This role is not specified.")

    def _on_propose_as_buyer(self, msg_id: int, dialogue_id: int, origin: str, target: int, proposals: PROPOSE_TYPES) -> None:
        """
        On Propose handler for buyer.

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

        :return: None
        """
        logger.debug("[{}]: on propose as buyer.".format(self.public_key))
        proposal = proposals[0]
        transaction_id = generate_transaction_id(self.public_key, origin, dialogue_id)
        transaction = self._from_proposal_to_transaction(proposal,
                                                         transaction_id,
                                                         is_buyer=True,
                                                         counterparty=origin)
        if self._is_profitable_transaction_as_buyer(transaction):
            logger.debug("[{}]: Accepting propose (as buyer).".format(self.public_key))
            self._accept_propose_as_buyer(msg_id, dialogue_id, origin, target, proposals)
        # TODO skip counter-propose
        else:
            logger.debug("[{}]: Declining propose (as buyer).".format(self.public_key))
            self.send_decline(msg_id + 1, dialogue_id, origin, msg_id)
            self._delete_dialogue_id(origin, dialogue_id)

    def _on_propose_as_seller(self, msg_id: int, dialogue_id: int, origin: str, target: int, proposals: PROPOSE_TYPES) -> None:
        """
        On Propose handler for seller.

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

        :return: None
        """
        logger.debug("[{}]: on propose as seller.".format(self.public_key))
        proposal = proposals[0]
        transaction_id = generate_transaction_id(origin, self.public_key, dialogue_id)
        transaction = self._from_proposal_to_transaction(proposal,
                                                         transaction_id,
                                                         is_buyer=False,
                                                         counterparty=origin)
        if self._is_profitable_transaction_as_seller(transaction):
            logger.debug("[{}]: Accepting propose (as seller).".format(self.public_key))
            self._accept_propose_as_seller(msg_id, dialogue_id, origin, target, proposals)
        # TODO skip counter-propose
        else:
            logger.debug("[{}]: Declining propose (as seller)".format(self.public_key))
            self.send_decline(msg_id + 1, dialogue_id, origin, msg_id)
            self._delete_dialogue_id(origin, dialogue_id)

    def _accept_propose_as_seller(self, msg_id: int, dialogue_id: int, origin: str, target: int, proposals: PROPOSE_TYPES) -> None:
        """
        Accept a propose as a seller.
        The parameters are the same of the main 'on_propose' methods.

        :return: None
        """
        logger.debug("[{}]: accept propose as seller".format(self.public_key))

        # compute the transaction request from the propose.
        proposal = proposals[0]
        dialogue_label = (origin, dialogue_id)
        transaction_id = generate_transaction_id(self.public_key, origin, dialogue_id)
        transaction = self._from_proposal_to_transaction(proposal=proposal,
                                                         transaction_id=transaction_id,
                                                         is_buyer=False,
                                                         counterparty=origin)
        # lock state
        logger.debug("[{}]: Locking the current state (as seller).".format(self.public_key))
        self._lock_state_as_seller(transaction)

        # add to pending acceptances
        acceptance_id = msg_id + 1
        self._pending_acceptances[dialogue_label][acceptance_id] = transaction

        # send accept
        self.send_accept(acceptance_id, dialogue_id, origin, msg_id)

    def _accept_propose_as_buyer(self, msg_id: int, dialogue_id: int, origin: str, target: int, proposals: PROPOSE_TYPES) -> None:
        """
        Accept a propose as a buyer.
        The parameters are the same of the main 'on_propose' methods.

        :return: None
        """
        logger.debug("[{}]: accept propose as buyer".format(self.public_key))

        # compute the transaction request from the propose.
        proposal = proposals[0]
        dialogue_label = (origin, dialogue_id)
        transaction_id = generate_transaction_id(self.public_key, origin, dialogue_id)
        transaction = self._from_proposal_to_transaction(proposal=proposal,
                                                         transaction_id=transaction_id,
                                                         is_buyer=True,
                                                         counterparty=origin)
        # lock state
        logger.debug("[{}]: Locking the current state (as buyer).".format(self.public_key))
        self._lock_state_as_buyer(transaction)

        # add to pending acceptances
        acceptance_id = msg_id + 1
        self._pending_acceptances[dialogue_label][acceptance_id] = transaction

        # send accept
        self.send_accept(acceptance_id, dialogue_id, origin, msg_id)

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
                     .format(self.public_key, msg_id, dialogue_id, origin, target))

        buyer_pbk, seller_pbk = (self.public_key, origin) if dialogue_id in self._dialogues_as_buyer \
            else (origin, self.public_key)
        transaction_id = generate_transaction_id(buyer_pbk, seller_pbk, dialogue_id)
        self._remove_lock(transaction_id)

        self._delete_dialogue_id(origin, dialogue_id)

        self._start_loop()

    def on_accept(self, msg_id: int, dialogue_id: int, origin: str, target: int) -> None:
        """
        On Accept handler.

        :param msg_id: the message id
        :param dialogue_id: the dialogue id
        :param origin: the public key of the message sender.
        :param target: the targeted message id to which this message is a response.

        :return: None
        """
        logger.debug("[{}]: on_accept: msg_id={}, dialogue_id={}, origin={}, target={}"
                     .format(self.public_key, msg_id, dialogue_id, origin, target))

        dialogue_label = (origin, dialogue_id)  # type: DIALOGUE_LABEL
        acceptance_id = target
        if dialogue_label in self._pending_acceptances and acceptance_id in self._pending_acceptances[dialogue_label]:
            self._on_match_accept(msg_id, dialogue_id, origin, target)
        else:
            self._on_accept(msg_id, dialogue_id, origin, target)

    def _on_accept(self, msg_id: int, dialogue_id: int, origin: str, target: int) -> None:
        dialogue_label = (origin, dialogue_id)  # type: DIALOGUE_LABEL
        is_buyer = dialogue_label in self._dialogues_as_buyer
        is_seller = dialogue_label in self._dialogues_as_seller
        if is_buyer:
            self._on_accept_as_buyer(msg_id, dialogue_id, origin, target)
        elif is_seller:
            self._on_accept_as_seller(msg_id, dialogue_id, origin, target)
        else:
            raise Exception("This dialogue id is not specified.")

    def _on_accept_as_buyer(self, msg_id: int, dialogue_id: int, origin: str, target: int):
        """
        Handles accept of buyer.
        :return: None
        """
        transaction = self._recover_pending_proposal(dialogue_id, origin, target)
        if self._is_profitable_transaction_as_buyer(transaction):
            logger.debug("[{}]: Locking the current state (buyer).".format(self.public_key))
            self._lock_state_as_buyer(transaction)
            self.submit_transaction_to_controller(transaction)
            self.send_accept(msg_id + 1, dialogue_id, origin, msg_id)
        else:
            logger.debug("[{}]: Decline the accept (as buyer).".format(self.public_key))
            self.send_decline(msg_id + 1, dialogue_id, origin, msg_id)

    def _on_accept_as_seller(self, msg_id: int, dialogue_id: int, origin: str, target: int):
        """
        Handles accept of seller.
        :return: None
        """
        transaction = self._recover_pending_proposal(dialogue_id, origin, target)
        if self._is_profitable_transaction_as_seller(transaction):
            logger.debug("[{}]: Locking the current state (seller).".format(self.public_key))
            self._lock_state_as_seller(transaction)
            self.submit_transaction_to_controller(transaction)
            self.send_accept(msg_id + 1, dialogue_id, origin, msg_id)
        else:
            logger.debug("[{}]: Decline the accept (as seller).".format(self.public_key))
            self.send_decline(msg_id + 1, dialogue_id, origin, msg_id)

    def _recover_pending_proposal(self, dialogue_id: int, origin: str, proposal_id: int) -> Transaction:
        """
        Recovers pending transaction proposal.
        :return: Transaction
        """
        dialogue_label = (origin, dialogue_id)
        assert dialogue_label in self._pending_proposals and proposal_id in self._pending_proposals[dialogue_label]
        transaction = self._pending_proposals[dialogue_label].pop(proposal_id)
        return transaction

    def _on_match_accept(self, msg_id: int, dialogue_id: int, origin: str, target: int):
        """
        Handles match accept.

        :return: None
        """
        # TODO implement at SDK level
        logger.debug("[{}]: on match accept".format(self.public_key))

        transaction = self._recover_pending_acceptance(dialogue_id, origin, target)
        self.submit_transaction_to_controller(transaction)

    def _recover_pending_acceptance(self, dialogue_id: int, origin: str, acceptance_id: int) -> Transaction:
        """
        Recovers pending transaction acceptance.
        :return: Transaction
        """
        dialogue_label = (origin, dialogue_id)
        assert dialogue_label in self._pending_acceptances and acceptance_id in self._pending_acceptances[dialogue_label]
        transaction = self._pending_acceptances[dialogue_label].pop(acceptance_id)
        return transaction

    def on_transaction_confirmed(self, tx_confirmation: TransactionConfirmation) -> None:
        """
        On Transaction confirmed handler.

        :param tx_confirmation: the transaction confirmation

        :return: None
        """
        logger.debug("[{}]: on transaction confirmed.".format(self.public_key))
        transaction = self._locks[tx_confirmation.transaction_id]
        self._agent_state.update(transaction, self._game_configuration.tx_fee)
        self._remove_lock(tx_confirmation.transaction_id)

        self._start_loop()

    def on_tac_error(self, error: Error) -> None:
        logger.error("[{}]: Received error from the controller. error_msg={}".format(self.public_key, error.error_msg))
        if error.error_code == ErrorCode.TRANSACTION_NOT_VALID:
            # if error in checking transaction, remove it from the pending transactions.
            start_idx_of_tx_id = len("Error in checking transaction: ")
            transaction_id = error.error_msg[start_idx_of_tx_id:]
            if transaction_id in self._locks:
                self._remove_lock(transaction_id)
            else:
                logger.warning("[{}]: Received error on unknown transaction id: {}".format(self.public_key, transaction_id))

    def _save_dialogue_id_as_buyer(self, origin: str, dialogue_id: int):
        dialogue_label = (origin, dialogue_id)
        assert dialogue_label not in self._all_dialogues
        assert dialogue_label not in self._dialogues_as_buyer
        self._all_dialogues.add(dialogue_label)
        self._dialogues_as_buyer.add(dialogue_label)

    def _save_dialogue_id_as_seller(self, origin: str, dialogue_id: int):
        dialogue_label = (origin, dialogue_id)
        logger.debug("[{}]: saving dialogue {}".format(self.public_key, dialogue_label))
        assert dialogue_label not in self._all_dialogues
        assert dialogue_label not in self._dialogues_as_seller
        self._all_dialogues.add(dialogue_label)
        self._dialogues_as_seller.add(dialogue_label)

    def _delete_dialogue_id(self, origin: str, dialogue_id: int):
        dialogue_label = (origin, dialogue_id)
        logger.debug("[{}]: deleting dialogue {}".format(self.public_key, dialogue_label))
        assert dialogue_label in self._all_dialogues
        assert dialogue_label in self._dialogues_as_buyer or dialogue_label in self._dialogues_as_seller

        self._all_dialogues.remove(dialogue_label)
        if dialogue_label in self._dialogues_as_buyer:
            self._dialogues_as_buyer.remove(dialogue_label)
        elif dialogue_label in self._dialogues_as_seller:
            self._dialogues_as_seller.remove(dialogue_label)
        else:
            assert False

    def _extract_info_from_propose(self, proposal: Description) -> Tuple[int, Dict[int, int]]:
        """
        From a propose (description), extract the price, the good ids and the quantities proposed.

        :param proposal: the description.
        :return: a tuple with (price, good ids, quantities)
        """
        data = copy.deepcopy(proposal.values)
        price = data.pop("price")
        quantity_by_good_id = {from_good_attribute_name_to_good_id(key): value for key, value in data.items()}
        return price, quantity_by_good_id

    def _is_profitable_transaction_as_buyer(self, transaction: Transaction) -> bool:
        """
        Is a profitable transaction for a buyer?
        - apply all the locks as buyer.
        - check if the transaction is consistent with the locks (enough money/holdings)
        - check that we gain score.

        :param transaction: the transaction
        :return: True if the transaction is good (as stated above), False otherwise.
        """

        state_after_locks = self._state_after_locks_as_buyer()

        if not state_after_locks.check_transaction_is_consistent(transaction, self._game_configuration.tx_fee):
            logger.debug("[{}]: the proposed transaction is not consistent with the state after locks.".format(self.public_key))
            return False

        proposal_delta_score = state_after_locks.get_score_diff_from_transaction(transaction, self._game_configuration.tx_fee)

        result = proposal_delta_score >= 0
        logger.debug("[{}]: is good proposal for buyer? {}: tx_id={}, "
                     "delta_score={}, "
                     "amount={}"
                     .format(self.public_key,
                             result,
                             transaction.transaction_id,
                             proposal_delta_score,
                             transaction.amount))
        return result

    def _is_profitable_transaction_as_seller(self, transaction: Transaction) -> bool:
        """
        Is a profitable transaction for a seller?
        - apply all the locks as seller.
        - check if the transaction is consistent with the locks (enough money/holdings)
        - check that we gain score.

        :param transaction: the transaction
        :return: True if the transaction is good (as stated above), False otherwise.
        """

        state_after_locks = self._state_after_locks_as_seller()

        if not state_after_locks.check_transaction_is_consistent(transaction, self._game_configuration.tx_fee):
            logger.debug("[{}]: the proposed transaction is not consistent with the state after locks.".format(self.public_key))
            return False

        proposal_delta_score = state_after_locks.get_score_diff_from_transaction(transaction, self._game_configuration.tx_fee)

        result = proposal_delta_score >= 0
        logger.debug("[{}]: is good proposal for seller? {}: tx_id={}, delta_score={}, amount={}"
                     .format(self.public_key, result, transaction.transaction_id,
                             proposal_delta_score, transaction.amount))
        return result

    def _from_proposal_to_transaction(self, proposal: Description, transaction_id: str,
                                      is_buyer: bool, counterparty: str) -> Transaction:
        """
        Create a transaction from a proposal.

        :param proposal:
        :param transaction_id:
        :param is_buyer:
        :param counterparty:
        :return: Transaction
        """
        price, quantity_by_good_id = self._extract_info_from_propose(proposal)
        transaction = Transaction(transaction_id, is_buyer, counterparty, price, quantity_by_good_id,
                                  sender=self.public_key)
        return transaction

    def _lock_state_as_buyer(self, transaction: Transaction) -> None:
        """
        Lock the state as buyer (assuming that the transaction is valid)
        That is, save the locking proposal. This step is needed to finalize the commit later.

        :param transaction: the transaction used to lock the state.
        :return: None
        """
        self._locks[transaction.transaction_id] = transaction
        self._locks_as_buyer[transaction.transaction_id] = transaction

    def _lock_state_as_seller(self, transaction: Transaction) -> None:
        """
        Lock the state as seller (assuming that the transaction is valid)
        That is, save the locking proposal. This step is needed to finalize the commit later.

        :param transaction: the transaction used to lock the state.
        :return: None
        """
        self._locks[transaction.transaction_id] = transaction
        self._locks_as_seller[transaction.transaction_id] = transaction

    def _state_after_locks_as_seller(self):
        """
        Apply all the locks to the current state of the seller. That is, assuming all
        the locked transactions will be successful.

        :return: the agent state with the locks applied to current state
        """
        transactions = list(self._locks_as_seller.values())
        state_after_locks = self._agent_state.apply(transactions, self._game_configuration.tx_fee)
        return state_after_locks

    def _state_after_locks_as_buyer(self):
        """
        Apply all the locks to the current state of the seller.

        :return: the agent state with the locks applied to current state
        """
        transactions = list(self._locks_as_buyer.values())
        state_after_locks = self._agent_state.apply(transactions, self._game_configuration.tx_fee)
        return state_after_locks

    def _remove_lock(self, transaction_id: str):
        """
        Try to remove a lock, given its id.

        :param transaction_id: the transaction id.
        :return: None
        """
        self._locks.pop(transaction_id, None)
        self._locks_as_buyer.pop(transaction_id, None)
        self._locks_as_seller.pop(transaction_id, None)

    def _get_supplied_goods_quantities(self) -> List[int]:
        """
        Wraps the function which determines supplied good quantities.

        :return: the vector of good quantities offered.
        """
        state_after_locks = self._state_after_locks_as_seller()
        return BaselineStrategy.supplied_good_quantities(state_after_locks.current_holdings)

    def _get_supplied_goods_ids(self) -> Set[int]:
        """
        Wraps the function which determines supplied good ids.

        :return: a list of supplied good ids
        """
        state_after_locks = self._state_after_locks_as_seller()
        return BaselineStrategy.supplied_good_ids(state_after_locks.current_holdings)

    def _get_demanded_goods_quantities(self) -> List[int]:
        """
        Wraps the function which determines demanded good quantities.

        :return: the vector of good quantities requested.
        """
        state_after_locks = self._state_after_locks_as_buyer()
        return BaselineStrategy.demanded_good_quantities(state_after_locks.current_holdings)

    def _get_demanded_goods_ids(self) -> Set[int]:
        """
        Wraps the function which determines demand.

        If there are locks as buyer, apply them.

        :return: a list of demanded good ids
        """
        state_after_locks = self._state_after_locks_as_buyer()
        return BaselineStrategy.demanded_good_ids(state_after_locks.current_holdings)

    def _get_seller_proposals(self) -> List[Description]:
        """
        Wraps the function which generates proposals from a seller.

        If there are locks as seller, it applies them.

        :return: a list of descriptions
        """
        state_after_locks = self._state_after_locks_as_seller()
        return BaselineStrategy.get_seller_proposals(state_after_locks.current_holdings, state_after_locks.utility_params)

    def _get_buyer_proposals(self) -> List[Description]:
        """
        Wraps the function which generates proposals from a buyer.

        If there are locks as buyer, it applies them.

        :return: a list of descriptions
        """
        state_after_locks = self._state_after_locks_as_buyer()
        return BaselineStrategy.get_buyer_proposals(state_after_locks.current_holdings, state_after_locks.utility_params, self._game_configuration.tx_fee)


class BaselineStrategy:
    def supplied_good_quantities(current_holdings: List[int]) -> List[int]:
        """
        Generates list of quantities which are supplied.

        :param current_holdings: a list of current good holdings
        :return: a list of quantities
        """
        return [q - 1 for q in current_holdings]

    def supplied_good_ids(current_holdings: List[int]) -> Set[int]:
        """
        Generates set of good ids which are supplied.

        :param current_holdings: a list of current good holdings
        :return: a set of ids
        """
        return {good_id for good_id, quantity in enumerate(current_holdings) if quantity > 1}

    def demanded_good_quantities(current_holdings: List[int]) -> List[int]:
        """
        Generates list of quantities which are demanded.

        :param current_holdings: a list of current good holdings
        :return: a list of quantities
        """
        return [1 for _ in current_holdings]

    def demanded_good_ids(current_holdings: List[int]) -> Set[int]:
        """
        Generates set of good ids which are demanded.

        :param current_holdings: a list of current good holdings
        :return: a set of ids
        """
        return {good_id for good_id, quantity in enumerate(current_holdings)}

    def get_seller_proposals(current_holdings: List[int], utility_params: List[int]) -> List[Description]:
        """
        Generates proposals from the seller.

        :param current_holdings: a list of current good holdings
        :param utility_params: a list of utility params
        :param tx_fee: the transaction fee
        :return: a list of proposals in Description form
        """
        quantities = BaselineStrategy.supplied_good_quantities(current_holdings)
        proposals = []
        zeroslist = [0] * len(quantities)
        rounding_adjustment = 0.01
        for good_id in range(len(quantities)):
            if quantities[good_id] == 0: continue
            lis = copy.deepcopy(zeroslist)
            lis[good_id] = 1
            desc = get_goods_quantities_description(lis, True)
            delta_holdings = [i * -1 for i in lis]
            marginal_utility_from_single_good = marginal_utility(utility_params, current_holdings, delta_holdings) * -1
            desc.values["price"] = round(marginal_utility_from_single_good, 2) + rounding_adjustment
            proposals.append(desc)
        return proposals

    def get_buyer_proposals(current_holdings: List[int], utility_params: List[int], tx_fee: float) -> List[Description]:
        """
        Generates proposals from the buyer.

        :param current_holdings: a list of current good holdings
        :param utility_params: a list of utility params
        :param tx_fee: the transaction fee
        :return: a list of proposals in Description form
        """
        quantities = BaselineStrategy.demanded_good_quantities(current_holdings)
        proposals = []
        zeroslist = [0] * len(quantities)
        rounding_adjustment = 0.01
        for good_id in range(len(quantities)):
            lis = copy.deepcopy(zeroslist)
            lis[good_id] = 1
            desc = get_goods_quantities_description(lis, True)
            delta_holdings = lis
            marginal_utility_from_single_good = marginal_utility(utility_params, current_holdings, delta_holdings)
            desc.values["price"] = round(marginal_utility_from_single_good, 2) - tx_fee - rounding_adjustment
            proposals.append(desc)
        return proposals


def main():
    args = parse_arguments()
    agent = BaselineAgent(public_key=args.public_key, oef_addr=args.oef_addr, oef_port=args.oef_port)

    agent.connect()
    agent.search_for_tac()

    logger.debug("Running agent...")
    agent.run()


if __name__ == '__main__':
    main()

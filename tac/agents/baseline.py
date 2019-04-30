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
import copy
import logging
import pprint
import random
import re
import time
from collections import defaultdict
from typing import List, Optional, Dict, Set, Tuple

from oef.messages import CFP_TYPES, PROPOSE_TYPES
from oef.query import Query
from oef.schema import Description

from tac.core import NegotiationAgent
from tac.helpers.misc import generate_transaction_id, build_query, get_goods_quantities_description, \
    TAC_BUYER_DATAMODEL_NAME, from_good_attribute_name_to_good_id, TAC_SELLER_DATAMODEL_NAME
from tac.protocol import GameData, Transaction, TransactionConfirmation, Error

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
    The baseline agent simply tries to buy goods it does not currently have and sell goods it already has more than once.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.tac_search_id = set()

        self._all_dialogues = set()  # type: Set[DIALOGUE_LABEL]
        self._dialogues_as_buyer = set()  # type: Set[DIALOGUE_LABEL]
        self._dialogues_as_seller = set()  # type: Set[DIALOGUE_LABEL]

        self._pending_proposals = defaultdict(lambda: {})  # type: Dict[DIALOGUE_LABEL, Dict[MESSAGE_ID, Transaction]]
        self._pending_acceptances = defaultdict(lambda: {})  # type: Dict[DIALOGUE_LABEL, Dict[MESSAGE_ID, Transaction]]

        self._locks = {}  # type: Dict[str, Transaction]
        self._locks_as_buyer = {}  # type: Dict[str, Transaction]
        self._locks_as_seller = {}  # type: Dict[str, Transaction]

    def on_start(self, game_data: GameData) -> None:
        """
        Handle the 'start' event (baseline agent):

        - Register to the OEF as a seller, offering all excess good instances.
        - Register to the OEF as a buyer, demanding all missing good instances.
        - Search for the goods needed, and eventually start a negotiation as the buyer.
        - Search for the goods requested, and eventually start a negotiation as the seller.

        :param game_data: the game data

        :return: None
        """
        self._register_as_seller()
        # self._register_as_buyer() TODO include the symmetry, eventually.
        time.sleep(1.0)
        self._search_for_sellers()
        # self._search_for_buyers() TODO include the symmetry, eventually.

    def _register_as_seller(self) -> None:
        """
        Register to the Service Directory as a seller, listing the goods supplied.

        :return: None
        """
        logger.debug("[{}]: Register as seller.".format(self.public_key))
        goods_supplied_description = self._get_goods_supplied_description()
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
        Get the description of the supplied goods, following a baseline policy.
        That is, a description with the following structure:
        >>> description = {
        ...     "good_01": 1,
        ...     "good_02": 0,
        ...     #...
        ...
        ... }
        >>>
        where the keys indicate the good and the values the quantity that the agent wants to sell.

        The baseline agent's policy is to sell all the goods in excess, hence keeping at least one instance for every good.

        :return: the description (to advertise on the Service Directory).
        """
        desc = get_goods_quantities_description(self._get_supplied_goods_quantities(), True)
        return desc

    def _get_supplied_goods_quantities(self) -> List[int]:
        """
        Wraps the function which determines supplied quantities.

        :return: a list of demanded quantities
        """
        result = self._agent_state.get_excess_goods_quantities()
        # set the positive quantities at one - duplicates doesn't count
        result = [1 if q >= 1 else 0 for q in result]
        return result

    def _get_goods_demanded_description(self) -> Description:
        """
        Get the description of the demanded goods, following a baseline policy.
        That is, a description with the following structure:
        >>> description = {
        ...     "good_01": 1,
        ...     "good_02": 0,
        ...     #...
        ...
        ... }
        >>>
        where the keys indicate the good and the values the quantity that the agent wants to buy.

        The baseline agent's policy is to buy all the goods which increase her utility.

        :return: the description (to advertise on the Service Directory).
        """
        desc = get_goods_quantities_description(self._get_demanded_goods_quantities(), False)
        return desc

    def _get_demanded_goods_quantities(self) -> List[int]:
        """
        Wraps the function which determines demanded quantities.

        :return: a list of demanded quantities
        """
        return self._agent_state.get_requested_quantities()

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

    # def _search_for_buyers(self) -> None:
    #     """
    #     Search on OEF core for buyers and their demand.
    #
    #     :return: None
    #     """
    #     query = self._build_buyers_query()
    #     if query is None:
    #         logger.warning("[{}]: Not sending the query to the OEF because the agent supplies no goods.".format(self.public_key))
    #         return None
    #     else:
    #         logger.debug("[{}]: Search for buyers.".format(self.public_key))
    #         self.search_services(TAC_BUYER_SEARCH_ID, query)

    def _build_sellers_query(self) -> Optional[Query]:
        """
        Build the query to look for agents which supply the agent's demanded goods.

        :return the Query, or None.
        """
        demanded_goods_ids = self._get_demanded_goods_ids(apply_locks=True)

        if len(demanded_goods_ids) == 0:
            return None
        else:
            return build_query(demanded_goods_ids, True, self._agent_state.nb_goods)

    def _get_demanded_goods_ids(self, apply_locks: bool = False) -> Set[int]:
        """
        Wraps the function which determines demand.

        :param apply_locks: whether the locks as buyer must be taken into consideration.
        :return: a list of demanded good ids
        """
        if apply_locks is False:
            return self._agent_state.get_zero_quantity_goods_ids()
        else:
            # update the holdings with the buyer's lock
            current_holdings = self._agent_state.current_holdings
            for tx_id, transaction in self._locks_as_buyer.items():
                for good_id, quantity in transaction.quantities_by_good_id.items():
                    current_holdings[good_id] += quantity

            zero_quantity_good_ids = set(good_id for good_id, quantity in enumerate(current_holdings) if quantity == 0)
            return zero_quantity_good_ids

    # def _build_buyers_query(self) -> Optional[Query]:
    #     """
    #     Build the query to look for agents which demand the agent's supplied goods.
    #
    #     :return the Query, or None.
    #     """
    #     supplied_goods_ids = self._get_supplied_goods_ids()
    #
    #     if len(supplied_goods_ids) == 0:
    #         return None
    #     else:
    #         return build_query(supplied_goods_ids, False, self._agent_state.nb_goods)

    def _get_supplied_goods_ids(self, apply_locks: bool = False) -> Set[int]:
        """
        Wraps the function which determines supply.

        :param apply_locks: whether the locks as seller must be taken into consideration.
        :return: a list of supplied good ids
        """
        if apply_locks is False:
            return self._agent_state.get_excess_quantity_goods_ids()
        else:
            # update the holdings with the seller's lock
            current_holdings = self._agent_state.current_holdings
            for tx_id, transaction in self._locks_as_buyer.items():
                for good_id, quantity in transaction.quantities_by_good_id.items():
                    current_holdings[good_id] -= quantity

            excess_quantity_good_ids = set(good_id for good_id, quantity in enumerate(current_holdings) if quantity > 1)
            return excess_quantity_good_ids

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
            # self._on_buyers_search_result(agents)
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
            return
        for seller in sellers:
            dialogue_id = random.randint(0, 2 ** 31)
            logger.debug("[{}]: send_cfp_as_buyer: msg_id={}, dialogue_id={}, destination={}, target={}, query={}"
                         .format(self.public_key, STARTING_MESSAGE_ID, dialogue_id, seller, STARTING_MESSAGE_REF, query))
            self.send_cfp(STARTING_MESSAGE_ID, dialogue_id, seller, STARTING_MESSAGE_REF, query)
            self._register_dialogue_id_as_buyer(seller, dialogue_id)

    # def _on_buyers_search_result(self, buyers: List[str]) -> None:
    #     """
    #     Callback of the search result for agents which buy the goods the agent supplies.
    #
    #     The actions are:
    #     - build a CFP query to identify if any more goods are supplied and which ones
    #     - send a CFP to every agent found
    #
    #     if there is no need for any good, do nothing.
    #
    #     :param: buyers: a list of agent public keys.
    #
    #     :return: None
    #     """
    #
    #     logger.debug("[{}]: Found potential buyers: {}".format(self.public_key, buyers))
    #
    #     query = self._build_buyers_query()
    #     if query is None:
    #         logger.debug("[{}]: No longer supplying any goods...".format(self.public_key))
    #         return
    #     for buyer in buyers:
    #         dialogue_id = random.randint(0, 2 ** 31)
    #         logger.debug("[{}]: send_cfp_as_seller: msg_id={}, dialogue_id={}, destination={}, target={}, query={}"
    #                      .format(self.public_key, STARTING_MESSAGE_ID, dialogue_id, buyer, STARTING_MESSAGE_REF, query))
    #         self.send_cfp(STARTING_MESSAGE_ID, dialogue_id, buyer, STARTING_MESSAGE_REF, query)
    #         self._register_dialogue_id_as_seller(buyer, dialogue_id)

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
            # TODO should not be here, until we do not introduce symmetry.
            assert False
            # self._on_cfp_as_buyer(msg_id, dialogue_id, origin, target, query)

    def _on_cfp_as_seller(self, msg_id: int, dialogue_id: int, origin: str, target: int, query: CFP_TYPES) -> None:
        """
        On CFP handler for seller.

        - If the current holdings do not satisfy the CFP query, answer with a Decline
        - Otherwise, make a trivial proposal including all the goods supplied.

        :param msg_id: the message id
        :param dialogue_id: the dialogue id
        :param origin: the public key of the message sender.
        :param target: the targeted message id to which this message is a response.
        :param query: the query associated with the cfp.

        :return: None
        """
        self._register_dialogue_id_as_seller(origin, dialogue_id)
        goods_supplied_description = self._get_goods_supplied_description()
        utility_of_excess_goods = 0  # The utility of excess goods is zero by default. TODO to be fixed.
        goods_supplied_description.values["price"] = utility_of_excess_goods  # This is a naive strategy.
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
            proposals = [goods_supplied_description]
            logger.debug("[{}]: sending to {} a Propose{}".format(self.public_key, origin,
                                                                  pprint.pformat({
                                                                      "msg_id": new_msg_id,
                                                                      "dialogue_id": dialogue_id,
                                                                      "origin": origin,
                                                                      "target": msg_id,
                                                                      "propose": goods_supplied_description.values
                                                                  })))

            # store the proposed transaction in the pool of pending proposals.
            dialogue_label = (origin, dialogue_id)
            proposal_id = new_msg_id
            transaction_id = generate_transaction_id(origin, self.public_key, dialogue_id)
            transaction = self.from_proposal_to_transaction(proposal=goods_supplied_description,
                                                            transaction_id=transaction_id,
                                                            is_buyer=False,
                                                            counterparty=origin)
            self._pending_proposals[dialogue_label][proposal_id] = transaction

            # send the propose
            self.send_propose(new_msg_id, dialogue_id, origin, msg_id, proposals)


    # def _on_cfp_as_buyer(self, msg_id: int, dialogue_id: int, origin: str, target: int, query: CFP_TYPES) -> None:
    #     """
    #     On CFP handler for buyer.
    #
    #     - If the current demand does not satisfy the CFP query, answer with a Decline
    #     - Otherwise, make a trivial proposal including all the goods demanded.
    #
    #     :param msg_id: the message id
    #     :param dialogue_id: the dialogue id
    #     :param origin: the public key of the message sender.
    #     :param target: the targeted message id to which this message is a response.
    #     :param query: the query associated with the cfp.
    #
    #     :return: None
    #     """
    #     self._register_dialogue_id_as_buyer(origin, dialogue_id)
    #     goods_demanded_description = self._get_goods_demanded_description()
    #     utility_of_missing_goods = 0  # TODO to be fixed.
    #     goods_demanded_description.values["price"] = utility_of_missing_goods
    #     new_msg_id = msg_id + 1
    #     if not query.check(goods_demanded_description):
    #         logger.debug("[{}]: Current holdings do not satisfy CFP query.".format(self.public_key))
    #         logger.debug("[{}]: sending to {} a Decline{}".format(self.public_key, origin,
    #                                                               pprint.pformat({
    #                                                                   "msg_id": new_msg_id,
    #                                                                   "dialogue_id": dialogue_id,
    #                                                                   "origin": origin,
    #                                                                   "target": msg_id
    #                                                               })))
    #         self.send_decline(new_msg_id, dialogue_id, origin, msg_id)
    #     else:
    #         proposals = [goods_demanded_description]
    #         logger.debug("[{}]: sending to {} a Propose{}".format(self.public_key, origin,
    #                                                               pprint.pformat({
    #                                                                   "msg_id": new_msg_id,
    #                                                                   "dialogue_id": dialogue_id,
    #                                                                   "origin": origin,
    #                                                                   "target": msg_id,
    #                                                                   "propose": goods_demanded_description.values
    #                                                               })))
    #         self.send_propose(new_msg_id, dialogue_id, origin, msg_id, proposals)
    #
    #         dialogue_label = (origin, dialogue_id)
    #         proposal_id = (dialogue_label, new_msg_id)
    #         self._pending_proposals[proposal_id] = goods_demanded_description

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
            assert False
            # self._on_propose_as_seller(msg_id, dialogue_id, origin, target, proposals)
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
        transaction = self.from_proposal_to_transaction(proposal,
                                                        transaction_id,
                                                        is_buyer=True,
                                                        counterparty=origin)
        if self.is_good_transaction_as_buyer(transaction):
            logger.debug("[{}]: Accepting propose.".format(self.public_key))
            self._accept_propose_as_buyer(msg_id, dialogue_id, origin, target, proposals)
        # TODO skip counter-propose
        else:
            logger.debug("[{}]: Declining propose".format(self.public_key))
            self.send_decline(msg_id + 1, dialogue_id, origin, msg_id)
            self._unregister_dialogue_id(origin, dialogue_id)

    # def _on_propose_as_seller(self, msg_id: int, dialogue_id: int, origin: str, target: int, proposals: PROPOSE_TYPES) -> None:
    #     """
    #     On Propose handler for seller.
    #
    #     1. parse the propose object
    #     2. compute the score of the propose.
    #         - if the proposed transaction increases the score,
    #           send an accept and lock the state waiting for the matched accept.
    #         - otherwise, decline the propose.
    #
    #     :param msg_id: the message id
    #     :param dialogue_id: the dialogue id
    #     :param origin: the public key of the message sender.
    #     :param target: the targeted message id to which this message is a response.
    #     :param proposals: the proposals associated with the message.
    #
    #     :return: None
    #     """
    #     logger.debug("[{}]: on propose as seller".format(self.public_key))
    #     # The seller needs to check whether she still has the good in excess!
    #     proposal = proposals[0]
    #     transaction_id = generate_transaction_id(origin, self.public_key, dialogue_id)
    #     transaction = self.from_proposal_to_transaction(proposal,
    #                                                     transaction_id,
    #                                                     is_buyer=False,
    #                                                     counterparty=origin)
    #     if self.is_good_transaction_as_seller(transaction):
    #         self._accept_propose_as_seller(msg_id, dialogue_id, origin, target, proposals)
    #
    # def _accept_propose_as_seller(self, msg_id: int, dialogue_id: int, origin: str, target: int, proposals: PROPOSE_TYPES) -> None:
    #     """
    #     Accept a propose as a seller.
    #     The parameters are the same of the main 'on_propose' methods.
    #
    #     :return: None
    #     """
    #     logger.debug("[{}]: accept propose as seller".format(self.public_key))
    #
    #     # send accept
    #     acceptance_message_id = msg_id + 1
    #     dialogue_label = (origin, dialogue_id)
    #     acceptance_id = (dialogue_label, acceptance_message_id)
    #     self._pending_acceptances[acceptance_id] = proposals[0]
    #
    #     self.send_accept(acceptance_message_id, dialogue_id, origin, msg_id)

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
        transaction = self.from_proposal_to_transaction(proposal=proposal,
                                                        transaction_id=transaction_id,
                                                        is_buyer=True,
                                                        counterparty=origin)
        # lock state
        logger.debug("[{}]: Locking the current state (buyer).".format(self.public_key))
        self._lock_state_as_buyer(transaction)

        # add to pending acceptances
        acceptance_id = msg_id + 1
        self._pending_acceptances[dialogue_label][acceptance_id] = transaction

        # send accept
        self.send_accept(acceptance_id, dialogue_id, origin, msg_id)

    # def _accept_propose(self, msg_id: int, dialogue_id: int, origin: str, target: int, proposals: PROPOSE_TYPES,
    #                     is_buyer: bool) -> None:
    #     """
    #     Accept a propose.
    #
    #     msg_id, dialogue_id, origin, target and proposals are the same parameter of the `on_propose`.
    #
    #     :param is_buyer: whether the accept is sent as a buyer or as a seller.
    #     :return: None
    #     """
    #     # TODO assuming `proposals` is a list with only one description, and
    #     #   with the format {"good_01": quantity, ..., "price": price}
    #     assert len(proposals) == 1
    #     proposal = proposals[0]
    #     price, quantity_by_good_id = self._extract_info_from_propose(proposal)
    #
    #     buyer, seller = (self.public_key, origin) if is_buyer else (origin, self.public_key)
    #     transaction_id = generate_transaction_id(buyer, seller, dialogue_id)
    #     transaction_request = Transaction(transaction_id, is_buyer, origin, price, quantity_by_good_id)
    #     self.submit_transaction(transaction_request)
    #     self.send_accept(msg_id + 1, dialogue_id, origin, msg_id)
    #
    # def _improve_propose(self, price: int, quantity_by_good_id: Dict[int, int], current_score: int) -> Optional[Description]:
    #     """
    #     TODO
    #     Improve a proposal, if it's possible.
    #     :param price: the proposal to improve.
    #     :param quantity_by_good_id: the quantities proposed for each good id.
    #     :return: A counter proposal.
    #     """
    #     proposal_delta_score = -1
    #     new_price = price - 1
    #     while (new_price >= 0) & (proposal_delta_score < 0):
    #         after_score = self._agent_state.get_score_after_transaction(-new_price, quantity_by_good_id)
    #         proposal_delta_score = after_score - current_score
    #         new_price -= 1
    #
    #     if new_price >= 0 & proposal_delta_score >= 0:
    #         description_content = {"good_{:02d}".format(i): q for i, q in enumerate(quantity_by_good_id.values)}
    #
    #         if price is not None:
    #             description_content["price"] = new_price
    #
    #         seller_data_model = build_datamodel(self._agent_state.nb_goods, True)
    #         desc = Description(description_content, data_model=seller_data_model)
    #         return desc
    #     else:
    #         return None

    def on_decline(self, msg_id: int, dialogue_id: int, origin: str, target: int) -> None:
        logger.debug("[{}]: on_decline: msg_id={}, dialogue_id={}, origin={}, target={}"
                     .format(self.public_key, msg_id, dialogue_id, origin, target))

        buyer_pbk, seller_pbk = (self.public_key, origin) if dialogue_id in self._dialogues_as_buyer \
            else (origin, self.public_key)
        transaction_id = generate_transaction_id(buyer_pbk, seller_pbk, dialogue_id)
        self.remove_lock(transaction_id)

        self._unregister_dialogue_id(origin, dialogue_id)

    def on_accept(self, msg_id: int, dialogue_id: int, origin: str, target: int) -> None:
        logger.debug("[{}]: on_accept: msg_id={}, dialogue_id={}, origin={}, target={}"
                     .format(self.public_key, msg_id, dialogue_id, origin, target))

        dialogue_label = (origin, dialogue_id)  # type: DIALOGUE_LABEL
        acceptance_id = target
        if dialogue_label in self._pending_acceptances and acceptance_id in self._pending_acceptances[dialogue_label]:
            self.on_match_accept(msg_id, dialogue_id, origin, target)
        else:
            self._on_accept(msg_id, dialogue_id, origin, target)

    def _on_accept(self, msg_id: int, dialogue_id: int, origin: str, target: int) -> None:
        dialogue_label = (origin, dialogue_id)  # type: DIALOGUE_LABEL
        is_buyer = dialogue_label in self._dialogues_as_buyer
        is_seller = dialogue_label in self._dialogues_as_seller
        if is_buyer:
            assert False  # TODO only accept as seller.
            # self._on_accept_as_buyer(msg_id, dialogue_id, origin, target)
        elif is_seller:
            self._on_accept_as_seller(msg_id, dialogue_id, origin, target)
        else:
            raise Exception("This dialogue id is not specified.")

    # def _on_accept_as_buyer(self, msg_id: int, dialogue_id: int, origin: str, target: int):
    #     # TODO lock as buyer
    #     # TODO remove code redundancy
    #
    #     # recover the pending proposal
    #     dialogue_label = (origin, dialogue_id)
    #     proposal_id = (dialogue_label, target)
    #     assert proposal_id in self._pending_proposals
    #     proposal = self._pending_proposals.pop(proposal_id)
    #     price, quantity_by_good_id = self._extract_info_from_propose(proposal)
    #
    #     # generate transaction
    #     # transaction id: "${buyer}_${seller}_${dialogueId}
    #     is_buyer = dialogue_label in self._dialogues_as_buyer
    #     buyer_pbk, seller_pbk = (self.public_key, origin) if is_buyer else (origin, self.public_key)
    #     transaction_id = generate_transaction_id(buyer_pbk, seller_pbk, dialogue_id)
    #     candidate_transaction = Transaction(transaction_id, is_buyer, origin, price, quantity_by_good_id, sender=self.public_key)
    #     self.submit_transaction(candidate_transaction)
    #     self.send_accept(msg_id + 1, dialogue_id, origin, msg_id)

    def _on_accept_as_seller(self, msg_id: int, dialogue_id: int, origin: str, target: int):
        # recover the pending proposal
        dialogue_label = (origin, dialogue_id)
        proposal_id = target
        assert dialogue_label in self._pending_proposals and target in self._pending_proposals[dialogue_label]
        transaction = self._pending_proposals[dialogue_label].pop(proposal_id)

        if self.is_good_transaction_as_seller(transaction):
            logger.debug("[{}]: Locking the current state (seller).".format(self.public_key))
            # lock state
            self._lock_state_as_seller(transaction)

            # submit transaction
            self.submit_transaction(transaction)

            # send accept
            self.send_accept(msg_id + 1, dialogue_id, origin, msg_id)
        else:
            logger.debug("[{}]: Decline the accept.".format(self.public_key))
            self.send_decline(msg_id + 1, dialogue_id, origin, msg_id)

    def on_match_accept(self, msg_id: int, dialogue_id: int, origin: str, target: int):
        logger.debug("[{}]: on match accept".format(self.public_key))

        # recover pending transaction
        dialogue_label = (origin, dialogue_id)  # type: DIALOGUE_LABEL
        acceptance_id = target
        assert dialogue_label in self._pending_acceptances and acceptance_id in self._pending_acceptances[dialogue_label]
        transaction = self._pending_acceptances[dialogue_label].pop(acceptance_id)

        # submit transaction
        self.submit_transaction(transaction)

    def on_transaction_confirmed(self, tx_confirmation: TransactionConfirmation) -> None:
        logger.debug("[{}]: on transaction confirmed.".format(self.public_key))
        transaction = self._locks[tx_confirmation.transaction_id]
        self._agent_state.update(transaction)
        self.remove_lock(tx_confirmation.transaction_id)

        logger.debug("[{}]: update service directory and search for sellers.".format(self.public_key))
        self._register_as_seller()
        time.sleep(1.0)
        self._search_for_sellers()

    def on_tac_error(self, error: Error) -> None:
        logger.error("[{}]: Received error from the controller. error_msg={}".format(self.public_key, error.error_msg))
        # TODO string comparison on error messages is extremely harmful.
        #  Error codes MUST BE used. To fix the protobuf file asap, just used temporarily to make things work.
        if re.match(error.error_msg, "Error in checking transaction: .*"):
            # if error in checking transaction, remove it from the pending transactions.
            start_idx_of_tx_id = len("Error in checking transaction: ")
            transaction_id = error.error_msg[start_idx_of_tx_id:]
            if transaction_id in self._locks:
                self.remove_lock(transaction_id)
            else:
                # TODO in the simple case, we shouldn't receive a transaction error defined on unknown transaction id.
                assert False

    def _register_dialogue_id_as_buyer(self, origin: str, dialogue_id: int):
        dialogue_label = (origin, dialogue_id)
        assert dialogue_label not in self._all_dialogues
        assert dialogue_label not in self._dialogues_as_buyer
        self._all_dialogues.add(dialogue_label)
        self._dialogues_as_buyer.add(dialogue_label)

    def _register_dialogue_id_as_seller(self, origin: str, dialogue_id: int):
        dialogue_label = (origin, dialogue_id)
        assert dialogue_label not in self._all_dialogues
        assert dialogue_label not in self._dialogues_as_seller
        self._all_dialogues.add(dialogue_label)
        self._dialogues_as_seller.add(dialogue_label)

    def _unregister_dialogue_id(self, origin: str, dialogue_id: int):
        dialogue_label = (origin, dialogue_id)
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

    def is_good_transaction_as_buyer(self, transaction: Transaction) -> bool:
        """
        Is a good transaction for a buyer?
        - apply all the locks as buyer.
        - check if the transaction is consistent with the locks (enough money/holdings)
        - check that we gain score.

        :param transaction: the transaction
        :return: True if the transaction is good (as stated above), False otherwise.
        """
        # compute the future state after the locks - that is, assuming that all the pending transactions will be successful.
        buyer_locks = list(self._locks_as_buyer.values())
        state_after_locks = self._agent_state.apply(buyer_locks)

        if not state_after_locks.check_transaction(transaction):
            return False

        current_score = state_after_locks.get_score()
        next_score = state_after_locks.get_score_after_transaction(transaction)
        proposal_delta_score = next_score - current_score

        logger.debug("[{}] is good proposal for buyer? tx_id={}, delta_score={}, current_score={}, next_score={}"
                     .format(self.public_key, transaction.transaction_id, proposal_delta_score, current_score, next_score))
        return proposal_delta_score > transaction.amount

    def is_good_transaction_as_seller(self, transaction: Transaction) -> bool:
        """
        Is a good transaction for a seller?
        - apply all the locks as seller.
        - check if the transaction is consistent with the locks (enough money/holdings)
        - check that we gain score.

        :param transaction: the transaction
        :return: True if the transaction is good (as stated above), False otherwise.
        """

        # compute the future state after the locks - that is, assuming that all the pending transactions will be successful.
        seller_locks = list(self._locks_as_seller.values())
        state_after_locks = self._agent_state.apply(seller_locks)

        # if the transaction is not valid wrt the state after the locks, then it's not good
        if not state_after_locks.check_transaction(transaction):
            return False

        # check if we gain score with the transaction.
        current_score = state_after_locks.get_score()
        next_score = state_after_locks.get_score_after_transaction(transaction)
        proposal_delta_score = next_score - current_score

        logger.debug("[{}] is good proposal for seller? tx_id={}, delta_score={}, current_score={}, next_score={}"
                     .format(self.public_key, transaction.transaction_id, proposal_delta_score, current_score, next_score))

        # TODO notice the equality: we allow sellers to sell quantities with profit=0.
        return proposal_delta_score >= transaction.amount

    def from_proposal_to_transaction(self, proposal: Description, transaction_id: str,
                                     is_buyer: bool, counterparty: str) -> Transaction:
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

    def remove_lock(self, transaction_id: str):
        """
        Try to remove a lock, given its id.
        :param transaction_id: the transaction id.
        :return: None
        """
        self._locks.pop(transaction_id, None)
        self._locks_as_buyer.pop(transaction_id, None)
        self._locks_as_seller.pop(transaction_id, None)


def main():
    args = parse_arguments()
    agent = BaselineAgent(public_key=args.public_key, oef_addr=args.oef_addr, oef_port=args.oef_port)

    agent.connect()
    agent.register_to_tac()

    logger.debug("Running agent...")
    agent.run()


if __name__ == '__main__':
    main()


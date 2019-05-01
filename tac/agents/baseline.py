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
import time
from typing import List, Optional, Dict, Set, Tuple

from oef.messages import CFP_TYPES, PROPOSE_TYPES
from oef.query import Query
from oef.schema import Description

from tac.core import NegotiationAgent
from tac.helpers.misc import generate_transaction_id, build_datamodel, build_query
from tac.helpers.plantuml import plantuml_gen, PlantUMLGenerator
from tac.protocol import Register, Response, GameData, Transaction, TransactionConfirmation, Error

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


class BaselineAgent(NegotiationAgent):
    """
    The baseline agent simply tries to buy goods it does not currently have and sell goods it already has more than once.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.tac_search_id = set()

    def on_start(self, game_data: GameData) -> None:
        """
        Handle the 'start' event (baseline agent):

        - Register to the OEF as a seller, offering all excess good instances.
        - Search for the goods needed, and eventually start a negotiation as the buyer.

        :param game_data: the game data

        :return: None
        """
        self._register_as_seller()
        # self._register_as_buyer() # TODO
        time.sleep(1.0)
        self._search_for_sellers()
        # self._search_for_buyers() # TODO

    def on_cancelled(self):
        logger.debug("[{}]: Received cancellation from the controller. Stopping...".format(self.public_key))
        self.stop()

    def _register_as_seller(self) -> None:
        """
        Register to the Service Directory as a seller, listing the goods supplied.

        :return: None
        """
        goods_supplied_description = self._get_goods_supplied_description()
        self.register_service(0, goods_supplied_description)

    def _register_as_buyer(self) -> None:
        """
        Register to the Service Directory as a buyer, listing the goods demanded.

        :return: None
        """
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
        seller_data_model = build_datamodel(self._agent_state.nb_goods, True)
        desc = Description({"good_{:02d}".format(i): q
                            for i, q in enumerate(self._get_supplied_goods_quantities())},
                           data_model=seller_data_model)
        return desc

    def _get_supplied_goods_quantities(self) -> List[int]:
        """
        Wraps the function which determines supplied quantities.

        :return: a list of demanded quantities
        """
        return self._agent_state.get_excess_goods_quantities()

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
        buyer_data_model = build_datamodel(self._agent_state.nb_goods, False)
        desc = Description({"good_{:02d}".format(i): q
                            for i, q in enumerate(self._get_demanded_goods_quantities())},
                           data_model=buyer_data_model)
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
            return build_query(demanded_goods_ids, True, self._agent_state.nb_goods)

    def _get_demanded_goods_ids(self) -> Set[int]:
        """
        Wraps the function which determines demand.

        :return: a list of demanded good ids
        """
        return self._agent_state.get_zero_quantity_goods_ids()


    def _build_buyers_query(self) -> Optional[Query]:
        """
        Build the query to look for agents which demand the agent's supplied goods.

        :return the Query, or None.
        """
        supplied_goods_ids = self._get_supplied_goods_ids()

        if len(supplied_goods_ids) == 0:
            return None
        else:
            return build_query(supplied_goods_ids, False, self._agent_state.nb_goods)

    def _get_supplied_goods_ids(self) -> Set[int]:
        """
        Wraps the function which determines supply.

        :return: a list of supplied good ids
        """
        return self._agent_state.get_excess_quantity_goods_ids()

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
            return
        for seller in sellers:
            dialogue_id = random.randint(0, 100000)
            logger.debug("[{}]: send_cfp_as_buyer: msg_id={}, dialogue_id={}, destination={}, target={}, query={}"
                     .format(self.public_key, STARTING_MESSAGE_ID, dialogue_id, seller, STARTING_MESSAGE_REF, query))
            self.send_cfp(STARTING_MESSAGE_ID, dialogue_id, seller, STARTING_MESSAGE_REF, query) # TODO what identifies that this is a seller cfp?

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
            dialogue_id = random.randint(0, 100000)
            logger.debug("[{}]: send_cfp_as_seller: msg_id={}, dialogue_id={}, destination={}, target={}, query={}"
                     .format(self.public_key, STARTING_MESSAGE_ID, dialogue_id, buyer, STARTING_MESSAGE_REF, query))
            self.send_cfp(STARTING_MESSAGE_ID, dialogue_id, buyer, STARTING_MESSAGE_REF, query)

    def on_cfp(self, msg_id: int, dialogue_id: int, origin: str, target: int, query: CFP_TYPES) -> None:
        """
        On CFP dispatcher dispatches to correct handler.

        :param msg_id: the message id
        :param dialogue_id: the dialogue id
        :param origin: the public key of the message sender.
        :param target: the targetted message id to which this message is a response.
        :param query: the query associated with the cfp.

        :return: None
        """
        logger.debug("[{}]: on_cfp: msg_id={}, dialogue_id={}, origin={}, target={}, query={}"
                     .format(self.public_key, msg_id, dialogue_id, origin, target, query))
        # TODO
        if True:
            self._on_cfp_as_seller(msg_id, dialogue_id, origin, target, query)
            return
        elif False:
            self._on_cfp_as_buyer(msg_id, dialogue_id, origin, target, query)
            return
        else:
            raise Exception("This role is not specified.")

    def _on_cfp_as_seller(self, msg_id: int, dialogue_id: int, origin: str, target: int, query: CFP_TYPES) -> None:
        """
        On CFP handler for seller.

        - If the current holdings do not satisfy the CFP query, answer with a Decline
        - Otherwise, make a trivial proposal including all the goods supplied.

        :param msg_id: the message id
        :param dialogue_id: the dialogue id
        :param origin: the public key of the message sender.
        :param target: the targetted message id to which this message is a response.
        :param query: the query associated with the cfp.

        :return: None
        """
        goods_supplied_description = self._get_goods_supplied_description()
        utility_of_excess_goods = 0 # The utility of excess goods is zero by default.
        goods_supplied_description.values["price"] = utility_of_excess_goods # This is a naive strategy.
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
            self.send_propose(new_msg_id, dialogue_id, origin, msg_id, proposals)

            # transaction id: "${buyer}_${seller}_${dialogueId}
            transaction_id = generate_transaction_id(origin, self.public_key, dialogue_id)
            price, quantity_by_good_id = self._extract_info_from_propose(proposals[0])
            candidate_transaction = Transaction(transaction_id, False, origin, price, quantity_by_good_id)
            self.submit_transaction(candidate_transaction, only_store=True)

    def _on_cfp_as_buyer(self, msg_id: int, dialogue_id: int, origin: str, target: int, query: CFP_TYPES ) -> None:
        """
        On CFP handler for buyer.

        - If the current demand does not satisfy the CFP query, answer with a Decline
        - Otherwise, make a trivial proposal including all the goods demanded.

        :param msg_id: the message id
        :param dialogue_id: the dialogue id
        :param origin: the public key of the message sender.
        :param target: the targetted message id to which this message is a response.
        :param query: the query associated with the cfp.

        :return: None
        """
        pass

    def on_propose(self, msg_id: int, dialogue_id: int, origin: str, target: int, proposals: PROPOSE_TYPES) -> None:
        """
        On propose dispatcher.

        :param msg_id: the message id
        :param dialogue_id: the dialogue id
        :param origin: the public key of the message sender.
        :param target: the targetted message id to which this message is a response.
        :param query: the proposals associated with the message.

        :return: None
        """
        logger.debug("[{}]: on_propose: msg_id={}, dialogue_id={}, origin={}, target={}, proposals={}"
                     .format(self.public_key, msg_id, dialogue_id, origin, target, proposals))
        # TODO
        if True:
            self._on_propose_as_buyer(msg_id, dialogue_id, origin, target, proposals)
            return
        elif False:
            self._on_propose_as_seller(msg_id, dialogue_id, origin, target, proposals)
            return
        else:
            raise Exception("This role is not specified.")

    def _on_propose_as_buyer(self, msg_id: int, dialogue_id: int, origin: str, target: int, proposals: PROPOSE_TYPES) -> None:
        """
        On Propose handler for buyer.

        1. parse the propose object
        2. compute the score of the propose.
            - if the proposed transaction increases the score,
              send an accept and submit the transaction to the controller.
            - otherwise, decline the propose.

        :param msg_id: the message id
        :param dialogue_id: the dialogue id
        :param origin: the public key of the message sender.
        :param target: the targetted message id to which this message is a response.
        :param query: the proposals associated with the message.

        :return: None
        """
        assert len(proposals) == 1
        proposal = proposals[0]

        price, quantity_by_good_id = self._extract_info_from_propose(proposal)
        current_score = self._agent_state.get_score()
        after_score = self._agent_state.get_score_after_transaction(-price, quantity_by_good_id)
        proposal_delta_score = after_score - current_score
        new_msg_id = msg_id + 1

        if proposal_delta_score >= 0:
            logger.debug("[{}]: Accepting propose with proposal_delta_score={}, price={}".format(self.public_key, proposal_delta_score, price))
            self._accept_propose(new_msg_id, dialogue_id, origin, target, proposals, True)
        elif False: #(proposal_delta_score < 0) & (price > 0):
            counter_proposal = _improve_propose(price, quantity_by_good_id, current_score)
            if counter_proposal is not None:
                logger.debug("[{}]: sending to {} a CounterPropose{}".format(self.public_key, origin,
                                                                  pprint.pformat({
                                                                      "msg_id": new_msg_id,
                                                                      "dialogue_id": dialogue_id,
                                                                      "origin": origin,
                                                                      "target": msg_id,
                                                                      "propose": counter_proposal.values
                                                                  })))
                counter_proposals = [counter_proposal]
                self.send_propose(new_msg_id, dialogue_id, origin, msg_id, counter_proposals)
                new_price, new_quantity_by_good_id = self._extract_info_from_propose(counter_proposal)
                transaction_id = generate_transaction_id(self.public_key, origin, dialogue_id)
                candidate_transaction = Transaction(transaction_id, False, origin, new_price, new_quantity_by_good_id)
                self.submit_transaction(candidate_transaction, only_store=True)
            else:
                logger.debug("[{}]: Declining propose after checking for counter propose with proposal_delta_score={}, price={}".format(self.public_key, proposal_delta_score, price))
                self.send_decline(new_msg_id, dialogue_id, origin, msg_id)
        else:
            logger.debug("[{}]: Declining propose with proposal_delta_score={}, price={}".format(self.public_key, proposal_delta_score, price))
            self.send_decline(new_msg_id, dialogue_id, origin, msg_id)

    def _on_propose_as_seller(self, msg_id: int, dialogue_id: int, origin: str, target: int, proposals: PROPOSE_TYPES) -> None:
        """
        On Propose handler for seller.

        1. parse the propose object
        2. compute the score of the propose.
            - if the proposed transaction increases the score,
              send an accept and submit the transaction to the controller.
            - otherwise, decline the propose.

        :param msg_id: the message id
        :param dialogue_id: the dialogue id
        :param origin: the public key of the message sender.
        :param target: the targetted message id to which this message is a response.
        :param query: the proposals associated with the message.

        :return: None
        """
        # TODO the seller always accept because he's trying to sell all the excesses. It might change.
        # The seller needs to check whether she still has the good in excess!
        self._accept_propose(msg_id, dialogue_id, origin, target, proposals, False)

    def _improve_propose(self, price: int, quantity_by_good_id: Dict[int, int], current_score: int) -> Optional[Description]:
        """
        TODO
        Improve a proposal, if it's possible.
        :param price: the proposal to improve.
        :param quantity_by_good_id: the quantities proposed for each good id.
        :return: A counter proposal.
        """
        proposal_delta_score = -1
        new_price = price - 1
        while (new_price >= 0) & (proposal_delta_score < 0):
            after_score = self._agent_state.get_score_after_transaction(-new_price, quantity_by_good_id)
            proposal_delta_score = after_score - current_score
            new_price -= 1

        if new_price >=0 & proposal_delta_score >= 0:
            description_content = {"good_{:02d}".format(i): q for i, q in enumerate(quantity_by_good_id.values)}

            if price is not None:
                description_content["price"] = new_price

            seller_data_model = build_datamodel(self._agent_state.nb_goods, True)
            desc = Description(description_content, data_model=seller_data_model)
            return desc
        else:
            return None

    def on_decline(self, msg_id: int, dialogue_id: int, origin: str, target: int) -> None:
        logger.debug("[{}]: on_decline: msg_id={}, dialogue_id={}, origin={}, target={}"
                     .format(self.public_key, msg_id, dialogue_id, origin, target))

    def on_accept(self, msg_id: int, dialogue_id: int, origin: str, target: int) -> None:
        logger.debug("[{}]: on_accept: msg_id={}, dialogue_id={}, origin={}, target={}"
                     .format(self.public_key, msg_id, dialogue_id, origin, target))
        # TODO send transaction confirmation?

    def _accept_propose(self, msg_id: int, dialogue_id: int, origin: str, target: int, proposals: PROPOSE_TYPES,
                        is_buyer: bool) -> None:
        """
        Accept a propose.

        msg_id, dialogue_id, origin, target and proposals are the same parameter of the `on_propose`.

        :param is_buyer: whether the accept is sent as a buyer or as a seller.
        :return: None
        """
        # TODO assuming `proposals` is a list with only one description, and
        #   with the format {"good_01": quantity, ..., "price": price}
        assert len(proposals) == 1
        proposal = proposals[0]
        price, quantity_by_good_id = self._extract_info_from_propose(proposal)

        buyer, seller = (self.public_key, origin) if is_buyer else (origin, self.public_key)
        transaction_id = generate_transaction_id(buyer, seller, dialogue_id)
        transaction_request = Transaction(transaction_id, is_buyer, origin, price, quantity_by_good_id)
        self.submit_transaction(transaction_request)
        self.send_accept(msg_id + 1, dialogue_id, origin, msg_id)

    def _extract_info_from_propose(self, proposal: Description) -> Tuple[int, Dict[int, int]]:
        """
        From a propose (description), extract the price, the good ids and the quantities proposed.
        
        :param proposal: the description.
        :return: a tuple with (price, good ids, quantities)
        """
        data = copy.deepcopy(proposal.values)
        price = data.pop("price")
        quantity_by_good_id = {int(key[-2:]): value for key, value in data.items()}
        return price, quantity_by_good_id

    def on_transaction_confirmed(self, tx_confirmation: TransactionConfirmation) -> None:
        pass

    def on_tac_error(self, error: Error) -> None:
        logger.error("[{}]: Received error from the controller. error_msg={}".format(self.public_key, error.error_msg))


def main():
    args = parse_arguments()
    agent = BaselineAgent(public_key=args.public_key, oef_addr=args.oef_addr, oef_port=args.oef_port)

    agent.connect()
    agent.register_to_tac()

    logger.debug("Running agent...")
    agent.run()


if __name__ == '__main__':
    main()


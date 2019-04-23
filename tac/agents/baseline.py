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
from tac.helpers.misc import generate_transaction_id, build_seller_datamodel, _build_tac_sellers_query
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


# this is the search ID to be used to execute the search query.
TAC_SELLER_SEARCH_ID = 2


class BaselineAgent(NegotiationAgent):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.tac_search_id = set()

    def on_search_results(self, search_id: int, agents: List[str]):

        logger.debug("[{}]: search result: {} {}".format(self.public_key, search_id, agents))
        if search_id == TAC_SELLER_SEARCH_ID:
            self._on_tac_seller_search_result(agents)
            return
        else:
            raise Exception("Shouldn't be here.")

    def on_start(self, game_data: GameData) -> None:
        """
        Handle the 'start' event (baseline agent):

        - Register to the OEF as a seller, offering the duplicate good instances.
        - Search for the goods needed, and eventually start a negotiation as the buyer.
        """
        self._register_as_seller()
        time.sleep(1.0)
        self.search_tac_sellers()

    def _register_as_seller(self) -> None:
        """
        Register to the Service Directory as a seller, offering the good instances in excess.
        :return: None
        """
        desc = self.get_baseline_seller_description()
        self.register_service(0, desc)

    def on_transaction_confirmed(self, tx_confirmation: TransactionConfirmation) -> None:
        pass

    def on_tac_error(self, error: Error) -> None:
        logger.error("[{}]: Received error from the controller. error_msg={}".format(self.public_key, error.error_msg))

    def on_cfp(self, msg_id: int, dialogue_id: int, origin: str, target: int, query: CFP_TYPES):
        """
        On CFP handler for a baseline agent.

        - If the current holdings do not satisfy the CFP query, answer with a Decline
        - Otherwise, make a trivial proposal including all the goods in excess.

        """

        logger.debug("[{}]: on_cfp: msg_id={}, dialogue_id={}, origin={}, target={}, query={}"
                     .format(self.public_key, msg_id, dialogue_id, origin, target, query))

        seller_description = self.get_baseline_seller_description()
        price = self._agent_state.score_good_quantities(self._agent_state.get_excess_goods_quantities())
        seller_description.values["price"] = price
        if not query.check(seller_description):
            logger.debug("[{}]: Current holdings do not satisfy CFP query.".format(self.public_key))
            self.send_decline(msg_id + 1, dialogue_id, origin, msg_id)
            logger.debug("[{}]: sending to {} a Decline{}".format(self.public_key, origin,
                                                                  pprint.pformat({
                                                                      "msg_id": msg_id + 1,
                                                                      "dialogue_id": dialogue_id,
                                                                      "origin": origin,
                                                                      "target": target
                                                                  })))
        else:
            proposals = [seller_description]
            logger.debug("[{}]: sending to {} a Propose{}".format(self.public_key, origin,
                                                                  pprint.pformat({
                                                                      "msg_id": msg_id + 1,
                                                                      "dialogue_id": dialogue_id,
                                                                      "origin": origin,
                                                                      "target": target,
                                                                      "propose": seller_description.values
                                                                  })))
            self.send_propose(msg_id + 1, dialogue_id, origin, msg_id, proposals)

            # transaction id: "${buyer}_${seller}_${dialogueId}
            transaction_id = generate_transaction_id(origin, self.public_key, dialogue_id)
            price, quantity_by_good_id = self._extract_info_from_propose(proposals[0])
            candidate_transaction = Transaction(transaction_id, False, origin, price, quantity_by_good_id)
            self.submit_transaction(candidate_transaction, only_store=True)

    def on_propose(self, msg_id: int, dialogue_id: int, origin: str, target: int, proposals: PROPOSE_TYPES):
        """TODO Assume propose only when buyer."""
        logger.debug("[{}]: on_propose: msg_id={}, dialogue_id={}, origin={}, target={}, proposals={}"
                     .format(self.public_key, msg_id, dialogue_id, origin, target, proposals))

        self._on_propose_as_buyer(msg_id, dialogue_id, origin, target, proposals)

    def _on_propose_as_buyer(self, msg_id: int, dialogue_id: int, origin: str, target: int, proposals: PROPOSE_TYPES):
        """
        On Propose handler for baseline agents, when they take the role of a buyer.

        1. parse the propose object
        2. compute the score of the propose.
            - if the proposed transaction increases the score,
              send an accept and submit the transaction to the controller.
            - otherwise, decline the propose.
        """
        assert len(proposals) == 1
        proposal = proposals[0]

        price, quantity_by_good_id = self._extract_info_from_propose(proposal)
        current_score = self._agent_state.get_score()
        after_score = self._agent_state.get_score_after_transaction(-price, quantity_by_good_id)
        proposal_delta_score = after_score - current_score

        if proposal_delta_score > price + self._fee:
            logger.debug("Accepting propose: proposal_delta_score={}, price={}".format(proposal_delta_score, price))
            self._accept_propose(msg_id + 1, dialogue_id, origin, target, proposals, True)
        else:
            logger.debug("Declining propose: proposal_delta_score={}, price={}".format(proposal_delta_score, price))
            self.send_decline(msg_id + 1, dialogue_id, origin, msg_id)

    def on_decline(self, msg_id: int, dialogue_id: int, origin: str, target: int):
        logger.debug("[{}]: on_decline: msg_id={}, dialogue_id={}, origin={}, target={}"
                     .format(self.public_key, msg_id, dialogue_id, origin, target))

    def on_accept(self, msg_id: int, dialogue_id: int, origin: str, target: int):
        logger.debug("[{}]: on_accept: msg_id={}, dialogue_id={}, origin={}, target={}"
                     .format(self.public_key, msg_id, dialogue_id, origin, target))
        # TODO send transaction confirmation?

    def search_tac_sellers(self) -> None:
        query = self.build_tac_sellers_query()
        if query is None:
            logger.warning("Not sending the query to the OEF because the agent already have all the goods.")
            return None
        else:
            self.search_services(TAC_SELLER_SEARCH_ID, query)

    def _on_propose_as_seller(self, msg_id: int, dialogue_id: int, origin: str, target: int, proposals: PROPOSE_TYPES):
        # TODO the seller always accept because he's trying to sell all the excesses. It might change.
        self._accept_propose(msg_id, dialogue_id, origin, target, proposals, False)

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

    def _get_zero_quantity_goods_ids(self) -> Set[int]:
        """
        Get the set of good ids for which we only have a quantity equal to zero.
        :return: a set of good ids.
        """
        zero_quantity_goods_ids = set(map(lambda x: x[0],
                                          filter(lambda x: x[1] == 0,
                                                 enumerate(self._agent_state.current_holdings))))
        return zero_quantity_goods_ids

    def build_tac_sellers_query(self) -> Optional[Query]:
        """Build the query to look for the needed goods (that is, the ones with zero count)

        :return the Query, or None if the agent already have at least one instance for every good."""
        zero_quantity_goods_ids = self._get_zero_quantity_goods_ids()

        if len(zero_quantity_goods_ids) == 0:
            return None
        else:
            return _build_tac_sellers_query(zero_quantity_goods_ids, self._agent_state.nb_goods)

    def _on_tac_seller_search_result(self, agents: List[str]) -> None:
        """
        Callback of the search result for seller agents.

        The actions are:
        - build a CFP query to search for the needed goods
        - send a CFP to every agent found

        if there is no need for any good, do nothing.

        :param: agents: a list of agent public keys.

        :return: None
        """

        logger.debug("[{}]: Found potential sellers: {}".format(self.public_key, agents))

        query = self.build_tac_sellers_query()
        if query is None:
            logger.debug("[{}]: No need for any more good...".format(self.public_key))
            return
        for seller in agents:
            dialogue_id = random.randint(0, 100000)
            self.send_cfp(1, dialogue_id, seller, 0, query)

    def get_baseline_seller_description(self) -> Description:
        """
        Get the TAC seller description, following a baseline policy.
        That is, a description with the following structure:
        >>> description = {
        ...     "good_01": 1,
        ...     "good_02": 0,
        ...     #...
        ...
        ... }
        >>>
         where the keys indicate the good and the values the quantity that the seller wants to sell.

         The baseline's policy is to sell all the goods in excess, hence keeping at least one instance for every good.

        :return: the description to advertise on the Service Directory.
        """
        seller_data_model = build_seller_datamodel(self._agent_state.nb_goods)
        desc = Description({"good_{:02d}".format(i): q
                            for i, q in enumerate(self._agent_state.get_excess_goods_quantities())},
                           data_model=seller_data_model)
        return desc

    def _build_description_from_quantities(self, quantities: List[int], price: Optional[int] = None) -> Description:
        """
        Build a description from a list of good quantities.
        :param quantities: the list of quantities, for every good.
        :param price: the price to put in the description
        :return: the description.
        """
        description_content = {"good_{:02d}".format(i): q for i, q in enumerate(quantities)}

        if price is not None:
            description_content["price"] = price

        data_model = build_seller_datamodel(self._agent_state.nb_goods)
        desc = Description(description_content, data_model=data_model)
        return desc


def main():
    args = parse_arguments()
    agent = BaselineAgent(public_key=args.public_key, oef_addr=args.oef_addr, oef_port=args.oef_port)

    agent.connect()
    agent.register_to_tac()

    logger.debug("Running agent...")
    agent.run()


if __name__ == '__main__':
    main()


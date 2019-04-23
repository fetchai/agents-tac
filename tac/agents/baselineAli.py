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
from typing import List, Optional, Dict, Set, Tuple, Any

import numpy as np
from oef.dialogue import DialogueAgent
from oef.messages import CFP_TYPES, PROPOSE_TYPES, OEFErrorOperation
from oef.query import Query, Constraint, GtEq, Or
from oef.schema import DataModel, AttributeSchema, Description

from tac.core import TACAgent
from tac.game import AgentState
from tac.helpers.misc import generate_transaction_id
from tac.helpers.plantuml import plantuml_gen, PlantUMLGenerator
from tac.protocol import Register, Response, GameData, Transaction, TransactionConfirmation

logger = logging.getLogger(__name__)


def parse_arguments():
    parser = argparse.ArgumentParser("baseline", description="Launch the baseline agent.")
    parser.add_argument("--public-key", default="baseline", help="Public key of the agent.")
    parser.add_argument("--oef-addr", default="127.0.0.1", help="TCP/IP address of the OEF Agent")
    parser.add_argument("--oef-port", default=3333, help="TCP/IP port of the OEF Agent")
    # parser.add_argument("--gui", action="store_true", help="Show the GUI.")

    return parser.parse_args()


class BaselineAgent(TACAgent):

    SEARCH_TAC_CONTROLLER_ID = 0
    SEARCH_TAC_SELLER_ID = 1
    SEARCH_TAC_BUYER_ID = 2

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.controller = None  # type: Optional[str]
        self.agent_state = None  # type: Optional[AgentState]
        self.seller_data_model = None  # type: Optional[DataModel]
        self.buyer_data_model = None  # type: Optional[DataModel]

        self.tac_search_id = set()

        self.negotiation_as_seller = set()  # type: Set[Tuple[str, int]]

        self.pending_transactions = {}  # type: Dict[str, Transaction]

    def on_search_result(self, search_id: int, agents: List[str]):
        logger.debug("[{}]: search result: {} {}".format(self.public_key, search_id, agents))
        super().on_search_result(search_id, agents)
        if self.SEARCH_TAC_CONTROLLER_ID == search_id:
            self._on_tac_controller_search_result(agents)
            return
        elif search_id == self.SEARCH_TAC_SELLER_ID:
            self._on_tac_seller_search_result(agents)
        else:
            raise Exception("Shouldn't be here.")

    def on_message(self, msg_id: int, dialogue_id: int, origin: str, content: bytes):
        msg = Response.from_pb(content)
        logger.debug("[{}]: Response from the TAC Controller '{}':\n{}".format(self.public_key, origin, str(msg)))

        if isinstance(msg, GameData):
            assert self.agent_state is None and self.controller is None
            self.controller = origin
            self.agent_state = AgentState(self.public_key, msg.money, list(msg.endowment), list(msg.preference), list(msg.preferences))
            logger.debug("[{}]: Score: {}".format(self.public_key, self.agent_state.get_score()))

            goods_quantities_attributes = [AttributeSchema("good_{:02d}".format(i), int, True)
                                           for i in range(self.agent_state.nb_goods)]
            price_attribute = AttributeSchema("price", int, False)
            self.seller_data_model = DataModel("tac_seller", goods_quantities_attributes + [price_attribute])
            self.buyer_data_model = DataModel("tac_buyer", goods_quantities_attributes + [price_attribute])

            self._register_as_seller_for_excessing_goods()
            # TODO remember this sleep for two second: it might change.
            time.sleep(2.0)
            self.search_tac_sellers()
        if isinstance(msg, TransactionConfirmation):
            transaction = self.pending_transactions.pop(msg.transaction_id)
            self.agent_state.update(transaction.buyer, transaction.amount, transaction.good_ids, transaction.quantities)

    def on_cfp(self, msg_id: int, dialogue_id: int, origin: str, target: int, query: CFP_TYPES):
        logger.debug("[{}]: on_cfp: msg_id={}, dialogue_id={}, origin={}, target={}, query={}"
                     .format(self.public_key, msg_id, dialogue_id, origin, target, query))

        # since we received a cfp, in this negotiation we take the role of the seller
        self.negotiation_as_seller.add((origin, dialogue_id))

        seller_description = self.get_baseline_seller_description()
        price = self.agent_state.score_good_quantities(self.agent_state.get_excess_goods_quantities())
        seller_description.values["price"] = price
        if not query.check(seller_description):
            self.send_decline(msg_id + 1, dialogue_id, origin, msg_id)
            logger.debug("[{}]: sending to {} a Decline{}".format(self.public_key, origin,
                                                                  pprint.pformat({
                                                                      "msg_id": msg_id + 1,
                                                                      "dialogue_id": dialogue_id,
                                                                      "origin": origin,
                                                                      "target": target
                                                                  })))
            plantuml_gen.decline_cfp(self.public_key, origin, dialogue_id)

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
            plantuml_gen.send_propose(self.public_key, origin, dialogue_id, seller_description)

            # add the proposal in the pending proposals.
            # transaction id: "${buyer}_${seller}_${dialogueId}
            transaction_id = generate_transaction_id(origin, self.public_key, dialogue_id)
            price, good_ids, quantities = self._extract_info_from_propose(proposals[0])

            candidate_transaction = Transaction(self.public_key, transaction_id, False, origin, price, good_ids,
                                                quantities)
            self.pending_transactions[transaction_id] = candidate_transaction

    def on_propose(self, msg_id: int, dialogue_id: int, origin: str, target: int, proposals: PROPOSE_TYPES):
        logger.debug("[{}]: on_propose: msg_id={}, dialogue_id={}, origin={}, target={}, proposals={}"
                     .format(self.public_key, msg_id, dialogue_id, origin, target, proposals))

        dialogue_key = (origin, dialogue_id)

        if dialogue_key in self.negotiation_as_seller:
            self._on_propose_as_seller(msg_id, dialogue_id, origin, target, proposals)
        else:
            self._on_propose_as_buyer(msg_id, dialogue_id, origin, target, proposals)

    def on_decline(self, msg_id: int, dialogue_id: int, origin: str, target: int):
        logger.debug("[{}]: on_decline: msg_id={}, dialogue_id={}, origin={}, target={}"
                     .format(self.public_key, msg_id, dialogue_id, origin, target))
        dialogue_key = (origin, dialogue_id)
        self.negotiation_as_seller.discard(dialogue_key)

    def on_accept(self, msg_id: int, dialogue_id: int, origin: str, target: int):
        logger.debug("[{}]: on_accept: msg_id={}, dialogue_id={}, origin={}, target={}"
                     .format(self.public_key, msg_id, dialogue_id, origin, target))
        # TODO send transaction confirmation?
        dialogue_key = (origin, dialogue_id)
        self.negotiation_as_seller.discard(dialogue_key)

    def search_tac_agents(self) -> None:
        self.search_services(self.SEARCH_TAC_CONTROLLER_ID, Query([Constraint("version", GtEq(1))]))

    def search_tac_sellers(self) -> None:
        query = self.build_tac_sellers_query()
        if query is None:
            logger.warning("Not sending the query to the OEF because the agent already have all the goods.")
        else:
            requested_goods = self._get_zero_quantity_goods_ids()
            self.search_services(self.SEARCH_TAC_SELLER_ID, query, additional_msg=str(requested_goods))

    def _on_propose_as_buyer(self, msg_id: int, dialogue_id: int, origin: str, target: int, proposals: PROPOSE_TYPES):
        assert len(proposals) == 1
        proposal = proposals[0]

        price, good_ids, quantities = self._extract_info_from_propose(proposal)
        current_score = self.agent_state.get_score()
        after_score = self.agent_state.get_score_after_transaction(-price, quantities)
        proposal_score = after_score - current_score

        if proposal_score > price:
            logger.debug("Accepting propose: proposal_score={}, price={}".format(proposal_score, price))
            self._accept_propose(msg_id, dialogue_id, origin, target, proposals, True)
        else:
            logger.debug("Declining propose: proposal_score={}, price={}".format(proposal_score, price))
            self.send_decline(msg_id + 1, dialogue_id, origin, msg_id)

        # TODO for later usage
        # counterpropose = self._improve_propose(proposal)
        #
        # # if the counterpropose is the same, just accept
        # if counterpropose.values == proposal.values:
        #     self._accept_propose(msg_id, dialogue_id, origin, target, proposals, True)
        #     return
        #
        # # if there is a way to improve the seller proposal, send a counter-propose
        # if counterpropose is not None:
        #     self.send_propose(msg_id + 1, dialogue_id, origin, msg_id, [counterpropose])
        #     plantuml_gen.send_propose(self.public_key, origin, dialogue_id, counterpropose)
        #     new_price, good_ids, new_quantities = self._extract_info_from_propose(counterpropose)
        #     transaction_id = generate_transaction_id(self.public_key, origin, dialogue_id)
        #     transaction_request = Transaction(self.public_key, transaction_id, True, origin, new_price, good_ids, new_quantities)
        #     self.pending_transactions[transaction_id] = transaction_request
        # # otherwise, decline the current proposal
        # else:
        #     self.send_decline(msg_id + 1, dialogue_id, origin, msg_id)

    def _on_propose_as_seller(self, msg_id: int, dialogue_id: int, origin: str, target: int, proposals: PROPOSE_TYPES):
        # TODO the seller always accept because he's trying to sell all the excesses. It might change.
        self._accept_propose(msg_id, dialogue_id, origin, target, proposals, False)

    def _improve_propose(self, proposal: Description) -> Optional[Description]:
        """
        Improve a proposal, if it's possible.
        :param proposal: the proposal to improve.
        :return: A better proposal, the same proposal, or None if it cannot be improved.
        """
        price, good_ids, quantities = self._extract_info_from_propose(proposal)

        # transform every quantity greater or equal than 1 into 1, because we don't want more than one copy of the same good.
        new_quantities = [1 if q >= 1 else 0 for q in quantities]
        # if there is a score equal to 0 and the quantity of the associated good is > 0, just remove it
        if any(s == 0 for s in self.agent_state.utilities):
            good_id_with_zero_score = self.agent_state.utilities.index(0)
            new_quantities[good_id_with_zero_score] = 0

        # compute the proposal score
        new_score = self.agent_state.score_good_quantities(new_quantities)
        # use the seller's price if the price is lower than our estimate.
        new_price = price if new_score < price else price

        # if all the new desired quantities are 0, return None - it's not possible to improve the current proposal
        if all(q == 0 for q in new_quantities):
            return None

        # if both the price and the quantities are the same, return the same proposal
        if new_quantities == quantities and new_price == price:
            return proposal
        # if the quantities or the price changed, build another proposal
        else:
            new_proposal = self._build_description_from_quantities(new_quantities, price=new_price)
            return new_proposal

    def _accept_propose(self, msg_id: int, dialogue_id: int, origin: str, target: int, proposals: PROPOSE_TYPES, is_buyer: bool):
        # TODO assuming proposals are just one, and of specific format.
        assert len(proposals) == 1
        proposal = proposals[0]
        price, good_ids, quantities = self._extract_info_from_propose(proposal)

        buyer, seller = (self.public_key, origin) if is_buyer else (origin, self.public_key)
        transaction_id = generate_transaction_id(buyer, seller, dialogue_id)
        transaction_request = Transaction(self.public_key, transaction_id, is_buyer, origin, price, good_ids, quantities)
        self.pending_transactions[transaction_id] = transaction_request
        self.send_message(0, 0, self.controller, transaction_request.serialize())
        plantuml_gen.add_drawable(
            PlantUMLGenerator.Transition(self.public_key, self.controller, str(transaction_request)))

        logger.debug("[{}]: send accept to '{}'".format(self.public_key, origin))
        self.send_accept(msg_id + 1, dialogue_id, origin, msg_id)
        plantuml_gen.add_drawable(
            PlantUMLGenerator.Transition(self.public_key, origin, "Accept({})".format(dialogue_id)))

    def _extract_info_from_propose(self, proposal: Description) -> Tuple[int, List[int], List[int]]:
        data = copy.deepcopy(proposal.values)
        price = data.pop("price")
        good_ids, quantities = zip(
            *map(lambda x: (int(x[0][-2:]), x[1]), list(data.items())))  # type: List[int], List[int]
        return price, good_ids, quantities

    def _get_zero_quantity_goods_ids(self) -> Set[int]:
        zero_quantity_goods_ids = set(map(lambda x: x[0],
                                          filter(lambda x: x[1] == 0,
                                                 enumerate(self.agent_state.current_holdings))))
        return zero_quantity_goods_ids

    def build_tac_sellers_query(self) -> Optional[Query]:
        """Build the query to look for the needed goods (that is, the ones with zero count)

        :return the Query, or None if the agent already have at least one instance for every good."""
        zero_quantity_goods_ids = self._get_zero_quantity_goods_ids()

        if len(zero_quantity_goods_ids) == 0: return None
        elif len(zero_quantity_goods_ids) == 1:
            query = Query([Constraint("good_{:02d}".format(next(iter(zero_quantity_goods_ids))), GtEq(1))],
                          model=self.seller_data_model)
        else:
            query = Query([Or([Constraint("good_{:02d}".format(good_id), GtEq(1)) for good_id in zero_quantity_goods_ids])],
                          model=self.seller_data_model)
        return query

    def _on_tac_controller_search_result(self, agents: List[str]):
        """
        Handler for search result of controller agents.
        :param agents: the list of controller agent ids.
        :return: None
        """
        logger.debug("[{}]: Agents found: {}".format(self.public_key, pprint.pformat(agents)))

        if len(agents) == 0:
            logger.debug("[{}]: No TAC Controller Agent found. Stopping...".format(self.public_key))
            self.stop()
            return

        # TODO remove assumption only one controller
        assert len(agents) <= 1
        controller_pb_key = agents[0]
        msg = Register(self.public_key)
        msg_pb = msg.to_pb()
        msg_bytes = msg_pb.SerializeToString()
        self.send_message(0, 0, controller_pb_key, msg_bytes)
        logger.debug("[{}]: Sending '{}' message to the TAC Controller {}"
                     .format(self.public_key, msg, controller_pb_key))

        plantuml_gen.add_drawable(PlantUMLGenerator.Transition(self.public_key, controller_pb_key, "Register"))

    def _on_tac_seller_search_result(self, agents: List[str]):
        logger.debug("[{}]: Found potential sellers: {}".format(self.public_key, agents))

        # find goods with zero quantity and build a CFP asking for any of them.
        query = self.build_tac_sellers_query()
        if query is None:
            logger.debug("[{}]: No need for any more good...".format(self.public_key))
            return
        for seller in agents:
            dialogue_id = random.randint(0, 100000)
            self.send_cfp(1, dialogue_id, seller, 0, query)
            plantuml_gen.send_cfp(self.public_key, seller, dialogue_id, self._get_zero_quantity_goods_ids())

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

         The baseline agent decides to sell everything in excess, but keeping the goods that

        :return: the description to advertise on the Service Directory.
        """
        desc = Description({"good_{:02d}".format(i): q
                            for i, q in enumerate(self.agent_state.get_excess_goods_quantities())},
                           data_model=self.seller_data_model)
        return desc

    def _build_description_from_quantities(self, quantities: List[int], price: Optional[int] = None):
        description_content = {"good_{:02d}".format(i): q for i, q in enumerate(quantities)}

        if price is not None:
            description_content["price"] = price

        desc = Description(description_content, data_model=self.seller_data_model)
        return desc

    def _register_as_seller_for_excessing_goods(self) -> None:
        desc = self.get_baseline_seller_description()
        self.register_service(0, desc)


def main():
    args = parse_arguments()
    agent = BaselineAgent(public_key=args.public_key, oef_addr=args.oef_addr, oef_port=args.oef_port)

    agent.connect()
    agent.search_tac_agents()

    logger.debug("Running agent...")
    agent.run()


if __name__ == '__main__':
    main()


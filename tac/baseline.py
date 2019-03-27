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
import logging
import pprint
import random
from typing import List, Optional, Tuple, Dict

from oef.messages import CFP_TYPES, PROPOSE_TYPES
from oef.query import Query, Constraint, GtEq, Or
from oef.schema import DataModel, AttributeSchema, Description

from tac.controller import ControllerAgent
from tac.core import TacAgent, GameState, GameTransaction
from tac.protocol import Register, Response, GameData, Transaction, TransactionConfirmation

logger = logging.getLogger(__name__)


def parse_arguments():
    parser = argparse.ArgumentParser("baseline", description="Launch the baseline agent.")
    parser.add_argument("--public-key", default="baseline", help="Public key of the agent.")
    parser.add_argument("--oef-addr", default="127.0.0.1", help="TCP/IP address of the OEF Agent")
    parser.add_argument("--oef-port", default=3333, help="TCP/IP port of the OEF Agent")
    # parser.add_argument("--gui", action="store_true", help="Show the GUI.")

    return parser.parse_args()


class BaselineAgent(TacAgent):
    SEARCH_TAC_CONTROLLER_ID = 0
    SEARCH_TAC_SELLER_ID = 1
    SEARCH_TAC_BUYER_ID = 2

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.controller = None  # type: Optional[str]
        self.game_state = None  # type: Optional[GameState]
        self.seller_data_model = None  # type: Optional[DataModel]
        self.buyer_data_model = None  # type: Optional[DataModel]

        self.tac_search_id = set()

        self.pending_transactions = {}  # type: Dict[str, Transaction]

    def search_tac_agents(self) -> None:
        self.search_services(self.SEARCH_TAC_CONTROLLER_ID, Query([Constraint("version", GtEq(1))],
                                                                  model=ControllerAgent.CONTROLLER_DATAMODEL))

    def search_tac_sellers(self) -> None:
        query = self.build_tac_sellers_query()
        if query is None:
            logger.warning("Not sending the query to the OEF because the agent already have all the goods.")
        else:
            self.search_services(self.SEARCH_TAC_SELLER_ID, query)

    def build_tac_sellers_query(self) -> Optional[Query]:
        """Build the query to look for the needed goods (that is, the ones with zero count

        :return the Query, or None if the agent already have at least one instance for every good."""
        zero_quantity_goods_ids = set(map(lambda x: x[0],
                                          filter(lambda x: x[1] == 0,
                                                 enumerate(self.game_state.current_holdings))))

        if len(zero_quantity_goods_ids) == 0: return None
        elif len(zero_quantity_goods_ids) == 1:
            query = Query([Constraint("good_{:02d}".format(next(iter(zero_quantity_goods_ids))), GtEq(1))])
        else:
            query = Query([Or([Constraint("good_{:02d}".format(good_id), GtEq(1)) for good_id in zero_quantity_goods_ids])])
        return query

    def on_search_result(self, search_id: int, agents: List[str]):
        if self.SEARCH_TAC_CONTROLLER_ID == search_id:
            self._on_tac_search_result(agents)
            return

        assert search_id == self.SEARCH_TAC_SELLER_ID

        # find goods with zero quantity and build a CFP asking for any of them.
        query = self.build_tac_sellers_query()
        if query is None: return
        for seller in agents:
            self.send_cfp(1, random.randint(0, 100000), seller, 0, query)

    def _on_tac_search_result(self, agents: List[str]):
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
        logger.debug("[{}]: Sending '{}' message to the TAC Controller {}"
                     .format(self.public_key, msg, controller_pb_key))
        self.send_message(0, 0, controller_pb_key, msg_bytes)

    def on_message(self, msg_id: int, dialogue_id: int, origin: str, content: bytes):
        msg = Response.from_pb(content)
        logger.debug("[{}]: Response from the TAC Controller '{}':\n{}".format(self.public_key, origin, str(msg)))

        if isinstance(msg, GameData):
            assert self.game_state is None and self.controller is None
            self.controller = origin
            self.game_state = GameState(msg.money, msg.endowment, msg.preference, msg.scores)
            logger.debug("[{}]: Score: {}".format(self.public_key, self.game_state.get_score()))

            goods_quantities_attributes = [AttributeSchema("good_{:02d}".format(i), int, True)
                                           for i in range(self.game_state.nb_goods)]
            price_attribute = AttributeSchema("price", int, False)
            self.seller_data_model = DataModel("tac_seller", goods_quantities_attributes + [price_attribute])
            self.buyer_data_model = DataModel("tac_buyer", goods_quantities_attributes + [price_attribute])

            self._register_as_seller_for_excessing_goods()
            self.search_tac_sellers()
        if isinstance(msg, TransactionConfirmation):
            transaction = self.pending_transactions.pop(msg.transaction_id)
            self.game_state.update(transaction.buyer, transaction.amount, transaction.good_ids, transaction.quantities)

    def get_baseline_seller_description(self) -> Description:
        """
        Get the TAC seller description, following a baseline policy.
        That is, a description with the following structure:
        >>> {
        ...     "good_01": 1,
        ...     "good_02": 0,
        ...     #...
        ...
        ... }
         where the keys indicate the good and the values the quantity that the seller wants to sell.

         The baseline agent decides to sell everything in excess, but keeping the goods that

        :return: the description to advertise on the Service Directory.
        """
        desc = Description({"good_{:02d}".format(i): q
                            for i, q in enumerate(self.game_state.get_excess_goods_quantities())},
                           data_model=self.seller_data_model)
        return desc

    def _register_as_seller_for_excessing_goods(self) -> None:
        desc = self.get_baseline_seller_description()
        self.register_service(0, desc)

    def on_cfp(self, msg_id: int, dialogue_id: int, origin: str, target: int, query: CFP_TYPES):
        logger.debug("[{}]: on_cfp: msg_id={}, dialogue_id={}, origin={}, target={}, query={}"
                     .format(self.public_key, msg_id, dialogue_id, origin, target, query))

        seller_description = self.get_baseline_seller_description()
        price = self.game_state.get_price_from_quantities_vector(self.game_state.get_excess_goods_quantities())
        seller_description.values["price"] = price
        if not query.check(seller_description):
            logger.debug("[{}]: sending to {} a Decline{}".format(self.public_key, origin,
                                                                  pprint.pformat({
                                                                      "msg_id": msg_id + 1,
                                                                      "dialogue_id": dialogue_id,
                                                                      "origin": origin,
                                                                      "target": target
                                                                  })))
            self.send_decline(msg_id + 1, dialogue_id, origin, target)
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
            self.send_propose(msg_id + 1, dialogue_id, origin, target, proposals)
            # add the proposal in the pending proposals.
            # transaction id: buyer_seller_dialogueId
            transaction_id = "{}_{}_{}".format(origin, self.public_key, dialogue_id)
            data = proposals[0].values
            price = data.pop("price")
            good_ids, quantities = zip(*map(lambda x: (int(x[0][-2:]), x[1]), list(data.items())))
            candidate_transaction = Transaction(self.public_key, transaction_id, False, origin, price, good_ids,
                                              quantities)
            self.pending_transactions[transaction_id] = candidate_transaction

    def on_propose(self, msg_id: int, dialogue_id: int, origin: str, target: int, proposals: PROPOSE_TYPES):
        # TODO assuming that I can receive a propose ONLY AS A BUYER
        logger.debug("[{}]: on_propose: msg_id={}, dialogue_id={}, origin={}, target={}, proposals={}"
                     .format(self.public_key, msg_id, dialogue_id, origin, target, proposals))

        assert len(proposals) == 1
        data = proposals[0].values
        price = data.pop("price")
        good_ids, quantities = zip(*map(lambda x: (int(x[0][-2:]), x[1]), list(data.items())))

        transaction_id = "{}_{}_{}".format(self.public_key, origin, dialogue_id)
        transaction_request = Transaction(self.public_key, transaction_id, True, origin, price, good_ids, quantities)
        self.pending_transactions[transaction_id] = transaction_request
        self.send_message(0, 0, self.controller, transaction_request.serialize())

        logger.debug("[{}]: send accept to '{}'".format(self.public_key, origin))
        self.send_accept(msg_id + 1, dialogue_id, origin, target)

    def on_decline(self, msg_id: int, dialogue_id: int, origin: str, target: int):
        logger.debug("[{}]: on_decline: msg_id={}, dialogue_id={}, origin={}, target={}"
                     .format(self.public_key, msg_id, dialogue_id, origin, target))

    def on_accept(self, msg_id: int, dialogue_id: int, origin: str, target: int):
        logger.debug("[{}]: on_accept: msg_id={}, dialogue_id={}, origin={}, target={}"
                     .format(self.public_key, msg_id, dialogue_id, origin, target))
        # TODO assuming that receive accept ONLY AS SELLER


def main():
    args = parse_arguments()
    agent = BaselineAgent(public_key=args.public_key, oef_addr=args.oef_addr, oef_port=args.oef_port)

    agent.connect()
    agent.search_tac_agents()

    logger.debug("Running agent...")
    agent.run()


if __name__ == '__main__':
    main()


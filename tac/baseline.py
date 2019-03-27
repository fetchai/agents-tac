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
from typing import List, Optional

from oef.query import Query, Constraint, Eq, GtEq
from oef.schema import DataModel, AttributeSchema, Description

from tac.controller import ControllerAgent
from tac.core import TacAgent, GameState
from tac.protocol import Register, Response, GameData, Transaction

logger = logging.getLogger(__name__)


def parse_arguments():
    parser = argparse.ArgumentParser("baseline", description="Launch the baseline agent.")
    parser.add_argument("--public-key", default="baseline", help="Public key of the agent.")
    parser.add_argument("--oef-addr", default="127.0.0.1", help="TCP/IP address of the OEF Agent")
    parser.add_argument("--oef-port", default=3333, help="TCP/IP port of the OEF Agent")
    # parser.add_argument("--gui", action="store_true", help="Show the GUI.")

    return parser.parse_args()


class BaselineAgent(TacAgent):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.controller = None  # type: Optional[ControllerAgent]
        self.game_state = None  # type: Optional[GameState]
        self.sell_data_model = None  # type: Optional[DataModel]
        self.buyer_data_model = None  # type: Optional[DataModel]

    def on_search_result(self, search_id: int, agents: List[str]):
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

            self.sell_data_model = DataModel("tac_seller", [
                AttributeSchema("good_{:02d}".format(i), int, True)
                for i in range(self.game_state.nb_goods)])
            self.buyer_data_model = DataModel("tac_buyer", [
                AttributeSchema("good_{:02d}".format(i), int, True)
                for i in range(self.game_state.nb_goods)])

            self._register_as_seller_for_excessing_goods()
            # send dummy transaction.
            # dest = "tac_agent_0" if self.public_key != "tac_agent_0" else "tac_agent_1"
            # self.send_message(0, 0, self.controller,
            #                   Transaction(self.public_key, 0, True, dest, 10, 0, 1).serialize())

    def _register_as_seller_for_excessing_goods(self) -> None:
        desc = Description({"good_{:02d}".format(k): v - 1 if v > 1 else 0
                            for k, v in enumerate(self.game_state.current_holdings)},
                           data_model=self.sell_data_model)
        self.register_service(0, desc)


def main():
    args = parse_arguments()
    agent = BaselineAgent(public_key=args.public_key, oef_addr=args.oef_addr, oef_port=args.oef_port)

    agent.connect()
    agent.search_services(0, Query([Constraint("version", GtEq(1))],
                                   model=ControllerAgent.CONTROLLER_DATAMODEL))

    logger.debug("Running agent...")
    agent.run()


if __name__ == '__main__':
    main()


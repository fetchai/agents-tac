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
from typing import List

from oef.query import Query, Constraint, Eq, GtEq

from tac.controller import ControllerAgent
from tac.core import TacAgent
from tac.protocol import Register, Response

logger = logging.getLogger("tac")


def parse_arguments():
    parser = argparse.ArgumentParser("baseline", description="Launch the baseline agent.")
    parser.add_argument("--public-key", default="baseline", help="Public key of the agent.")
    parser.add_argument("--oef-addr", default="127.0.0.1", help="TCP/IP address of the OEF Agent")
    parser.add_argument("--oef-port", default=3333, help="TCP/IP port of the OEF Agent")
    # parser.add_argument("--gui", action="store_true", help="Show the GUI.")

    return parser.parse_args()


class BaselineAgent(TacAgent):

    def on_search_result(self, search_id: int, agents: List[str]):
        logger.debug("Agents found: {}".format(pprint.pformat(agents)))

        # TODO remove assumption only one controller
        assert len(agents) <= 1
        controller_pb_key = agents[0]
        msg = Register(self.public_key)
        msg_pb = msg.to_pb()
        msg_bytes = msg_pb.SerializeToString()
        self.send_message(0, 0, controller_pb_key, msg_bytes)

    def on_message(self, msg_id: int, dialogue_id: int, origin: str, content: bytes):
        msg = Response.from_pb(content)
        logger.debug(msg)


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


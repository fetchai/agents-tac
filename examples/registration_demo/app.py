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
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------

"""Show how an agent can register for the TAC"""
import logging
import pprint
from typing import List

from oef.query import Query, GtEq, Constraint

from tac.protocol import Register, Response

from tac.core import TACAgent

logger = logging.getLogger("tac")


class SimpleRegisteringAgent(TACAgent):

    def on_search_result(self, search_id: int, agents: List[str]):
        logger.debug("Agents found: {}".format(pprint.pformat(agents)))

        if len(agents) == 0:
            logger.debug("No TAC Controller Agent found. Stopping...")
            self.stop()
            return

        controller_pb_key = agents[0]
        msg = Register()
        msg_pb = msg.to_pb()
        msg_bytes = msg_pb.SerializeToString()
        logger.debug("Sending '{}' message to the TAC Controller {}"
                     .format(msg, controller_pb_key))
        self.send_message(0, 0, controller_pb_key, msg_bytes)

    def on_message(self, msg_id: int, dialogue_id: int, origin: str, content: bytes):
        msg = Response.from_pb(content)
        logger.debug("Response from the TAC Controller '{}': {}".format(origin, str(msg)))
        self.stop()


if __name__ == '__main__':
    agent = SimpleRegisteringAgent("simple_agent", "127.0.0.1", 3333)
    agent.connect()
    agent.search_services(0, Query([Constraint("version", GtEq(1))]))
    agent.run()

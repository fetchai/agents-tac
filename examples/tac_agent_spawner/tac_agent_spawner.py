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

"""Spawn several TAC agents."""
import asyncio
import logging
import pprint
import uuid
from typing import List, Optional
import argparse

from oef.query import Query, GtEq, Constraint

from tac.protocol import Register, Response, GameData

from tac.core import TacAgent, GameState

logger = logging.getLogger("tac")


def parse_arguments():
    parser = argparse.ArgumentParser("tac_agent_spawner")
    parser.add_argument("N", type=int, help="Number of TAC agent to run.")

    arguments = parser.parse_args()
    return arguments


class SimpleTacCAgent(TacAgent):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.game_state = None  # type: Optional[GameState]

    def on_search_result(self, search_id: int, agents: List[str]):
        logger.debug("Agents found: {}".format(pprint.pformat(agents)))

        if len(agents) == 0:
            logger.debug("No TAC Controller Agent found. Stopping...")
            self.stop()
            return

        controller_pb_key = agents[0]
        msg = Register(self.public_key)
        msg_pb = msg.to_pb()
        msg_bytes = msg_pb.SerializeToString()
        logger.debug("Sending '{}' message to the TAC Controller {}"
                     .format(msg, controller_pb_key))
        self.send_message(0, 0, controller_pb_key, msg_bytes)

    def on_message(self, msg_id: int, dialogue_id: int, origin: str, content: bytes):
        msg = Response.from_pb(content)
        logger.debug("[{}]: Response from the TAC Controller '{}': {}".format(self.public_key, origin, str(msg)))

        if isinstance(msg, GameData):
            assert self.game_state is None
            self.game_state = GameState(msg.money, msg.endowment, msg.preference, msg.scores)
            logger.debug("[{}]: {}".format(self.public_key, str(self.game_state)))


if __name__ == '__main__':

    arguments = parse_arguments()

    agents = [SimpleTacCAgent("simple_agent_" + str(i), "127.0.0.1", 3333) for i in range(arguments.N)]
    for a in agents:
        a.connect()
        a.search_services(0, Query([Constraint("version", GtEq(1))]))

    asyncio.gather(*[a.async_run() for a in agents])
    asyncio.get_event_loop().run_forever()

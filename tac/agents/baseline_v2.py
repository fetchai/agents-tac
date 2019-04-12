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

"""Baseline agent - version 2"""

import argparse
import asyncio
import datetime
import logging
from typing import Optional, Dict, Set, Tuple

from oef.messages import CFP_TYPES, OEFErrorOperation
from oef.query import Query, Constraint, Eq
from oef.schema import DataModel

from tac.core import NegotiationAgent
from tac.protocol import Transaction, GameData, Error, TransactionConfirmation

logger = logging.getLogger(__name__)


def parse_arguments():
    parser = argparse.ArgumentParser("baseline", description="Launch the baseline agent.")
    parser.add_argument("--public-key", default="baseline", help="Public key of the agent.")
    parser.add_argument("--oef-addr", default="127.0.0.1", help="TCP/IP address of the OEF Agent")
    parser.add_argument("--oef-port", default=3333, help="TCP/IP port of the OEF Agent")
    # parser.add_argument("--gui", action="store_true", help="Show the GUI.")

    return parser.parse_args()


class BaselineAgentV2(NegotiationAgent):

    def __init__(self, public_key: str, oef_addr: str, oef_port: int = 3333, **kwargs) -> None:
        super().__init__(public_key, oef_addr, oef_port, **kwargs)

    async def on_start(self, game_data: GameData) -> None:
        print("Called on_start")

    async def on_transaction_confirmed(self, tx_confirmation: TransactionConfirmation) -> None:
        pass

    async def on_tac_error(self, error: Error) -> None:
        pass

    async def on_connection_error(self, operation: OEFErrorOperation) -> None:
        pass

    async def on_new_cfp(self, msg_id: int, dialogue_id: int, from_: str, target: int, query: CFP_TYPES) -> None:
        pass


async def main():
    args = parse_arguments()
    start_time = datetime.datetime.now() + datetime.timedelta(0, 5)
    agent = BaselineAgentV2(public_key=args.public_key, oef_addr=args.oef_addr, oef_port=args.oef_port,
                            start_time=start_time)

    await agent.async_connect()
    agent_task = asyncio.ensure_future(agent.async_run())

    # result = await agent.search(Query([Constraint("pow", Eq(True))]))
    result = await agent.search(Query([Constraint("pow", Eq(True))]), callback=lambda x, y: print(y))
    print(result)

    logger.debug("Running agent...")
    await asyncio.sleep(3.0)


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())


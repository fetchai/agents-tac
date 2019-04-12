# -*- coding: utf-8 -*-
import argparse
import asyncio
import time
from typing import List, Dict

from oef.messages import OEFErrorOperation, CFP_TYPES
from oef.query import Query, Constraint, GtEq

from tac.agents.controller import ControllerAgent
from tac.core import NegotiationAgent
from tac.protocol import Error, TransactionConfirmation, GameData


def parse_arguments():
    parser = argparse.ArgumentParser("experimental", description="Launch the experimental agent.")
    parser.add_argument("--public-key", default="experimental", help="Public key of the agent.")
    parser.add_argument("--oef-addr", default="127.0.0.1", help="TCP/IP address of the OEF Agent")
    parser.add_argument("--oef-port", default=3333, help="TCP/IP port of the OEF Agent")
    # parser.add_argument("--gui", action="store_true", help="Show the GUI.")

    return parser.parse_args()


class ExperimentalAgent(NegotiationAgent):

    def __init__(self, public_key: str, oef_addr: str, oef_port: int = 3333, **kwargs) -> None:
        super().__init__(public_key, oef_addr, oef_port, **kwargs)

    async def search_controllers(self):
        result = await self.search(Query([Constraint("version", GtEq(1))]))
        return result

    async def on_start(self, game_data: GameData) -> None:
        pass

    async def on_transaction_confirmed(self, tx_confirmation: TransactionConfirmation) -> None:
        pass

    async def on_tac_error(self, error: Error) -> None:
        pass

    async def on_new_cfp(self, msg_id: int, dialogue_id: int, from_: str, target: int, query: CFP_TYPES) -> None:
        pass

    async def on_connection_error(self, operation: OEFErrorOperation) -> None:
        pass


async def main():
    args = parse_arguments()
    agent = ExperimentalAgent(public_key=args.public_key, oef_addr=args.oef_addr, oef_port=args.oef_port)

    await agent.async_connect()
    # launch the task for processing messages in the background
    agent_task = asyncio.ensure_future(agent.async_run())

    agents = await agent.search_controllers()
    print("Search result: ", agents)


if __name__ == '__main__':
    tac_controller = ControllerAgent("tac_controller_experimental")
    tac_controller.connect()
    tac_controller.register()
    time.sleep(1.0)
    asyncio.get_event_loop().run_until_complete(main())


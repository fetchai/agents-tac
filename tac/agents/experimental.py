# -*- coding: utf-8 -*-
import argparse
import asyncio
import time
from typing import List, Dict

from oef.query import Query, Constraint, GtEq

from tac.agents.controller import ControllerAgent
from tac.core import NegotiationAgent


def parse_arguments():
    parser = argparse.ArgumentParser("experimental", description="Launch the experimental agent.")
    parser.add_argument("--public-key", default="baseline", help="Public key of the agent.")
    parser.add_argument("--oef-addr", default="127.0.0.1", help="TCP/IP address of the OEF Agent")
    parser.add_argument("--oef-port", default=3333, help="TCP/IP port of the OEF Agent")
    # parser.add_argument("--gui", action="store_true", help="Show the GUI.")

    return parser.parse_args()


class ExperimentalAgent(NegotiationAgent):

    def __init__(self, public_key: str, oef_addr: str, oef_port: int = 3333, **kwargs) -> None:
        super().__init__(public_key, oef_addr, oef_port, **kwargs)
        self.pending_searches = {}  # type: Dict[int, asyncio.Event]
        self.search_results = {}  # type: Dict[int, List[str]]

    async def on_search_result(self, search_id: int, agents: List[str]):
        if search_id in self.pending_searches:
            self.search_results[search_id] = agents
            self.pending_searches[search_id].set()

    async def sync_search_services(self, search_id, q: Query) -> List[str]:
        self.search_services(search_id, q)
        event = asyncio.Event()
        self.pending_searches[search_id] = event
        await event.wait()
        result = self.search_results[search_id]
        return result

    async def search_controllers(self):
        result = await self.sync_search_services(0, Query([Constraint("version", GtEq(1))]))
        return result


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


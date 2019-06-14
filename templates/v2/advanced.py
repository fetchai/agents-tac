#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Template agent, to complete by the developer."""

import argparse
import logging

from tac.agents.v2.base.strategy import Strategy
from tac.agents.v2.examples.baseline import BaselineAgent

logger = logging.getLogger(__name__)


def parse_arguments():
    parser = argparse.ArgumentParser("my_agent", description="Launch my agent.")
    parser.add_argument("--name", default="my_agent", help="Name of the agent")
    parser.add_argument("--oef-addr", default="127.0.0.1", help="TCP/IP address of the OEF Agent")
    parser.add_argument("--oef-port", default=3333, help="TCP/IP port of the OEF Agent")

    return parser.parse_args()


class MyStrategy(Strategy):
    """
    My strategy implementation.
    """

    def __init__(self, register_as: str = 'both', search_for: str = 'both', is_world_modeling: bool = False):
        super().__init__(register_as, search_for, is_world_modeling)

        raise NotImplementedError("Your agent must implement the interface defined in Strategy.")


def main():
    args = parse_arguments()

    strategy = MyStrategy(register_as='both', search_for='both', is_world_modeling=False)
    agent = BaselineAgent(name=args.name, oef_addr=args.oef_addr, oef_port=args.oef_port, strategy=strategy)

    try:
        agent.start()
    finally:
        agent.stop()


if __name__ == '__main__':
    main()

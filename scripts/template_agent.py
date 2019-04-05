#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Template agent to complete."""

import argparse

from tac.agents.baseline import BaselineAgent
from tac.core import TacAgent


def parse_arguments():
    parser = argparse.ArgumentParser("baseline", description="Launch the baseline agent.")
    parser.add_argument("--oef-addr", default="127.0.0.1", help="TCP/IP address of the OEF Agent")
    parser.add_argument("--oef-port", default=3333, help="TCP/IP port of the OEF Agent")

    return parser.parse_args()


class MyAgent(TacAgent):
    """To implement..."""


# TODO the fact that we run a baseline agent is a temporary set up.
def main():
    args = parse_arguments()
    agent = BaselineAgent(public_key="template_agent", oef_addr=args.oef_addr, oef_port=args.oef_port)

    agent.connect()
    agent.search_tac_agents()

    agent.run()


if __name__ == '__main__':
    main()

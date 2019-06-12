#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Template agent to complete."""

import argparse
import logging

from tac.agents.baseline import BaselineAgent

logger = logging.getLogger(__name__)


def parse_arguments():
    parser = argparse.ArgumentParser("baseline_agent", description="Launch my agent.")
    parser.add_argument("--public-key", default="template_baseline_agent", help="Public key of the agent.")
    parser.add_argument("--oef-addr", default="127.0.0.1", help="TCP/IP address of the OEF Agent")
    parser.add_argument("--oef-port", default=3333, help="TCP/IP port of the OEF Agent")
    parser.add_argument("--agent-gui", action="store_true", help="Show the GUI.")

    return parser.parse_args()


def main():
    args = parse_arguments()
    agent = BaselineAgent(public_key=args.public_key, oef_addr=args.oef_addr, oef_port=args.oef_port)

    agent.connect()
    agent.search_for_tac()

    logger.debug("Running baseline agent...")
    agent.run()


if __name__ == '__main__':
    main()

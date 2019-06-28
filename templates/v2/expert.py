#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Template agent, to complete by the developer."""

import argparse
import logging
from typing import Optional

from tac.agents.v2.agent import Agent
from tac.agents.v2.mail import FIPAMailBox, InBox, OutBox

logger = logging.getLogger(__name__)


def parse_arguments():
    parser = argparse.ArgumentParser("my_agent", description="Launch my agent.")
    parser.add_argument("--name", default="my_agent", help="Name of the agent")
    parser.add_argument("--oef-addr", default="127.0.0.1", help="TCP/IP address of the OEF Agent")
    parser.add_argument("--oef-port", default=10000, help="TCP/IP port of the OEF Agent")
    parser.add_argument("--in-box-timeout", type=float, default=1.0, help="The timeout in seconds during which the in box sleeps.")
    parser.add_argument("--private-key", default=None, help="Path to a file containing a private key in PEM format.")

    return parser.parse_args()


class MyAgent(Agent):
    """
    My agent implementation.
    """

    def __init__(self, name: str, oef_addr: str, oef_port: int, in_box_timeout: float, private_key_pem_path: Optional[str] = None):
        super().__init__(name, oef_addr, oef_port, private_key_pem_path)
        self.mail_box = FIPAMailBox(self.crypto.public_key, oef_addr, oef_port)
        self.in_box = InBox(self.mail_box, self.in_box_timeout)
        self.out_box = OutBox(self.mail_box)

        raise NotImplementedError("Your agent must implement the interface defined in Agent.")


def main():
    args = parse_arguments()

    agent = MyAgent(name=args.name, oef_addr=args.oef_addr, oef_port=args.oef_port, in_box_timeout=args.in_box_timeout, private_key_pem_path=args.private_key)

    try:
        agent.start()
    finally:
        agent.stop()


if __name__ == '__main__':
    main()

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

"""Template agent, to complete by the developer."""

import argparse
import logging
from typing import Optional

from tac.agents.v1.agent import Agent
from tac.agents.v1.mail import FIPAMailBox, InBox, OutBox

logger = logging.getLogger(__name__)


def parse_arguments():
    """Arguments parsing."""
    parser = argparse.ArgumentParser("my_agent", description="Launch my agent.")
    parser.add_argument("--name", default="my_agent", help="Name of the agent")
    parser.add_argument("--oef-addr", default="127.0.0.1", help="TCP/IP address of the OEF Agent")
    parser.add_argument("--oef-port", default=10000, help="TCP/IP port of the OEF Agent")
    parser.add_argument("--agent-timeout", type=float, default=1.0, help="The time in (fractions of) seconds to time out an agent between act and react.")
    parser.add_argument("--private-key-pem", default=None, help="Path to a file containing a private key in PEM format.")

    return parser.parse_args()


class MyAgent(Agent):
    """My agent implementation."""

    def __init__(self, name: str, oef_addr: str, oef_port: int, agent_timeout: float = 1.0, private_key_pem_path: Optional[str] = None):
        """Agent initialization."""
        super().__init__(name, oef_addr, oef_port, private_key_pem_path, agent_timeout)
        self.mailbox = FIPAMailBox(self.crypto.public_key, oef_addr, oef_port)

        raise NotImplementedError("Your agent must implement the interface defined in Agent.")


def main():
    """Run the script."""
    args = parse_arguments()

    agent = MyAgent(name=args.name, oef_addr=args.oef_addr, oef_port=args.oef_port, agent_timeout=args.agent_timeout, private_key_pem_path=args.private_key_pem)

    try:
        agent.start()
    finally:
        agent.stop()


if __name__ == '__main__':
    main()

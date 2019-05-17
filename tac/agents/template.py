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
import argparse
import logging

from tac.agents.baseline import BaselineAgent, BaselineStrategy

logger = logging.getLogger(__name__)


def parse_arguments():
    parser = argparse.ArgumentParser("my_agent", description="Launch my agent.")
    parser.add_argument("--public-key", default="my_agent", help="Public key of the agent.")
    parser.add_argument("--oef-addr", default="127.0.0.1", help="TCP/IP address of the OEF Agent")
    parser.add_argument("--oef-port", default=3333, help="TCP/IP port of the OEF Agent")
    # parser.add_argument("--gui", action="store_true", help="Show the GUI.")

    return parser.parse_args()


class MyAgent(BaselineAgent, BaselineStrategy):
    """
    My agent implementation.
    """

    def __init__(self, public_key: str, oef_addr: str, oef_port: int = 3333, service_registration_strategy: str = 'both', **kwargs):
        super().__init__(public_key, oef_addr, oef_port, service_registration_strategy, **kwargs)


def main():
    args = parse_arguments()
    agent = MyAgent(public_key=args.public_key, oef_addr=args.oef_addr, oef_port=args.oef_port)

    agent.connect()
    agent.search_for_tac()

    logger.debug("Running my agent...")
    agent.run()


if __name__ == '__main__':
    main()

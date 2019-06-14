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

"""Template agent, no modification required."""

import argparse
import logging

from tac.agents.v2.examples.strategy import BaselineStrategy
from tac.agents.v2.examples.baseline import BaselineAgent

logger = logging.getLogger(__name__)


def parse_arguments():
    parser = argparse.ArgumentParser("my_agent", description="Launch my agent.")
    parser.add_argument("--name", default="my_baseline_agent", help="Name of the agent.")
    parser.add_argument("--oef-addr", default="127.0.0.1", help="TCP/IP address of the OEF Agent")
    parser.add_argument("--oef-port", default=3333, help="TCP/IP port of the OEF Agent")

    return parser.parse_args()


def main():
    args = parse_arguments()

    strategy = BaselineStrategy(register_as='both', search_for='both', is_world_modeling=False)
    agent = BaselineAgent(name=args.name, oef_addr=args.oef_addr, oef_port=args.oef_port, strategy=strategy)

    try:
        agent.start()
    finally:
        agent.stop()


if __name__ == '__main__':
    main()

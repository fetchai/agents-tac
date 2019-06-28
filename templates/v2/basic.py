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

from tac.agents.v2.base.strategy import RegisterAs, SearchFor

from tac.agents.v2.examples.baseline import BaselineAgent
from tac.agents.v2.examples.strategy import BaselineStrategy
from tac.gui.dashboards.agent import AgentDashboard

logger = logging.getLogger(__name__)


def parse_arguments():
    parser = argparse.ArgumentParser("my_agent", description="Launch my agent.")
    parser.add_argument("--name", default="my_baseline_agent", help="Name of the agent.")
    parser.add_argument("--oef-addr", default="127.0.0.1", help="TCP/IP address of the OEF Agent")
    parser.add_argument("--oef-port", default=10000, help="TCP/IP port of the OEF Agent")
    parser.add_argument("--in-box-timeout", type=float, default=1.0, help="The timeout in seconds during which the in box sleeps.")
    parser.add_argument("--register-as", choices=['seller', 'buyer', 'both'], default='both', help="The string indicates whether the baseline agent registers as seller, buyer or both on the oef.")
    parser.add_argument("--search-for", choices=['sellers', 'buyers', 'both'], default='both', help="The string indicates whether the baseline agent searches for sellers, buyers or both on the oef.")
    parser.add_argument("--is-world-modeling", type=bool, default=False, help="Whether the agent uses a workd model or not.")
    parser.add_argument("--services-interval", type=int, default=10, help="The number of seconds to wait before doing another search.")
    parser.add_argument("--pending-transaction-timeout", type=int, default=30, help="The timeout in seconds to wait for pending transaction/negotiations.")
    parser.add_argument("--private-key", default=None, help="Path to a file containing a private key in PEM format.")
    parser.add_argument("--rejoin", action="store_true", default=False, help="Whether the agent is joining a running TAC.")
    parser.add_argument("--gui", action="store_true", help="Show the GUI.")
    parser.add_argument("--visdom_addr", type=str, default="localhost", help="IP address to the Visdom server")
    parser.add_argument("--visdom_port", type=int, default=8097, help="Port of the Visdom server")

    return parser.parse_args()


def main():
    args = parse_arguments()

    if args.gui:
        dashboard = AgentDashboard(agent_name=args.name, env_name=args.name)
    else:
        dashboard = None

    strategy = BaselineStrategy(register_as=RegisterAs(args.register_as), search_for=SearchFor(args.search_for), is_world_modeling=args.is_world_modeling)
    agent = BaselineAgent(name=args.name, oef_addr=args.oef_addr, oef_port=args.oef_port, in_box_timeout=args.in_box_timeout, strategy=strategy,
                          services_interval=args.services_interval, pending_transaction_timeout=args.pending_transaction_timeout,
                          dashboard=dashboard, private_key_pem_path=args.private_key)

    try:
        agent.start(rejoin=args.rejoin)
    finally:
        agent.stop()


if __name__ == '__main__':
    main()

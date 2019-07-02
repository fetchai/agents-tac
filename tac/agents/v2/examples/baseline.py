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
from typing import Optional

from tac.agents.v2.base.participant_agent import ParticipantAgent
from tac.agents.v2.base.strategy import Strategy, RegisterAs, SearchFor
from tac.agents.v2.examples.strategy import BaselineStrategy
from tac.gui.dashboards.agent import AgentDashboard


class BaselineAgent(ParticipantAgent):

    def __init__(self, name: str, oef_addr: str, oef_port: int, strategy: Strategy, agent_timeout: float = 1.0, max_reactions: int = 100, services_interval: int = 10,
                 pending_transaction_timeout: int = 30, dashboard: Optional[AgentDashboard] = None,
                 private_key_pem_path: Optional[str] = None):
        super().__init__(name, oef_addr, oef_port, strategy, agent_timeout, max_reactions, services_interval, pending_transaction_timeout, dashboard, private_key_pem_path)


def _parse_arguments():
    parser = argparse.ArgumentParser("BaselineAgent", description="Launch the BaselineAgent.")
    parser.add_argument("--name", type=str, default="baseline_agent", help="Name of the agent.")
    parser.add_argument("--oef-addr", default="127.0.0.1", help="TCP/IP address of the OEF Agent")
    parser.add_argument("--oef-port", default=10000, help="TCP/IP port of the OEF Agent")
    parser.add_argument("--agent-timeout", type=float, default=1.0, help="The time in (fractions of) seconds to time out an agent between act and react.")
    parser.add_argument("--max-reactions", type=int, default=100, help="The maximum number of reactions (messages processed) per call to react.")
    parser.add_argument("--register-as", choices=['seller', 'buyer', 'both'], default='both', help="The string indicates whether the baseline agent registers as seller, buyer or both on the oef.")
    parser.add_argument("--search-for", choices=['sellers', 'buyers', 'both'], default='both', help="The string indicates whether the baseline agent searches for sellers, buyers or both on the oef.")
    parser.add_argument("--is-world-modeling", type=bool, default=False, help="Whether the agent uses a workd model or not.")
    parser.add_argument("--services-interval", type=int, default=10, help="The number of seconds to wait before doing another search.")
    parser.add_argument("--pending-transaction-timeout", type=int, default=30, help="The timeout in seconds to wait for pending transaction/negotiations.")
    parser.add_argument("--gui", action="store_true", help="Show the GUI.")
    parser.add_argument("--visdom_addr", type=str, default="localhost", help="Address of the Visdom server.")
    parser.add_argument("--visdom_port", type=int, default=8097, help="Port of the Visdom server.")
    return parser.parse_args()


if __name__ == '__main__':

    args = _parse_arguments()
    if args.gui:
        dashboard = AgentDashboard(agent_name=args.name, env_name=args.name)
    else:
        dashboard = None

    strategy = BaselineStrategy(register_as=RegisterAs(args.register_as), search_for=SearchFor(args.search_for), is_world_modeling=args.is_world_modeling)
    agent = BaselineAgent(args.name, args.oef_addr, args.oef_port, strategy, args.agent_timeout, args.max_reactions, args.services_interval, args.pending_transaction_timeout, dashboard, args.private_key)

    try:
        agent.start()
    finally:
        agent.stop()

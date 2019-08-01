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
from typing import List, Optional, Set

from oef.schema import Description

from tac.gui.dashboards.agent import AgentDashboard
from tac.platform.game import WorldState
from tac.agents.v1.base.strategy import Strategy, RegisterAs, SearchFor
from tac.agents.v1.examples.baseline import BaselineAgent

logger = logging.getLogger(__name__)


def parse_arguments():
    """Arguments parsing."""
    parser = argparse.ArgumentParser("my_agent", description="Launch my agent.")
    parser.add_argument("--name", default="my_agent", help="Name of the agent")
    parser.add_argument("--oef-addr", default="127.0.0.1", help="TCP/IP address of the OEF Agent")
    parser.add_argument("--oef-port", default=10000, help="TCP/IP port of the OEF Agent")
    parser.add_argument("--agent-timeout", type=float, default=1.0, help="The time in (fractions of) seconds to time out an agent between act and react.")
    parser.add_argument("--max-reactions", type=int, default=100, help="The maximum number of reactions (messages processed) per call to react.")
    parser.add_argument("--register-as", choices=['seller', 'buyer', 'both'], default='both', help="The string indicates whether the baseline agent registers as seller, buyer or both on the oef.")
    parser.add_argument("--search-for", choices=['sellers', 'buyers', 'both'], default='both', help="The string indicates whether the baseline agent searches for sellers, buyers or both on the oef.")
    parser.add_argument("--is-world-modeling", type=bool, default=False, help="Whether the agent uses a workd model or not.")
    parser.add_argument("--services-interval", type=int, default=10, help="The number of seconds to wait before doing another search.")
    parser.add_argument("--pending-transaction-timeout", type=int, default=30, help="The timeout in seconds to wait for pending transaction/negotiations.")
    parser.add_argument("--private-key-pem", default=None, help="Path to a file containing a private key in PEM format.")
    parser.add_argument("--rejoin", action="store_true", default=False, help="Whether the agent is joining a running TAC.")
    parser.add_argument("--gui", action="store_true", help="Show the GUI.")
    parser.add_argument("--visdom-addr", type=str, default="localhost", help="IP address to the Visdom server")
    parser.add_argument("--visdom-port", type=int, default=8097, help="Port of the Visdom server")

    return parser.parse_args()


class MyStrategy(Strategy):
    """My strategy implementation."""

    def __init__(self, register_as: RegisterAs = RegisterAs.BOTH, search_for: SearchFor = SearchFor.BOTH, is_world_modeling: bool = False):
        """Strategy initialization."""
        super().__init__(register_as, search_for, is_world_modeling)

    def supplied_good_quantities(self, current_holdings: List[int]) -> List[int]:
        """
        To generate a list of quantities which are supplied.

        :param current_holdings: a list of current good holdings
        :return: a list of quantities
        """
        raise NotImplementedError("Your agent must implement this method.")

    def supplied_good_pbks(self, good_pbks: List[str], current_holdings: List[int]) -> Set[str]:
        """
        To generate a set of good pbks which are supplied.

        :param good_pbks: a list of good pbks
        :param current_holdings: a list of current good holdings
        :return: a set of pbks
        """
        raise NotImplementedError("Your agent must implement this method.")

    def demanded_good_quantities(self, current_holdings: List[int]) -> List[int]:
        """
        To generate a list of quantities which are demanded.

        :param current_holdings: a list of current good holdings
        :return: a list of quantities
        """
        raise NotImplementedError("Your agent must implement this method.")

    def demanded_good_pbks(self, good_pbks: List[str], current_holdings: List[int]) -> Set[str]:
        """
        To generate a set of good pbks which are demanded.

        :param good_pbks: a list of good pbks
        :param current_holdings: a list of current good holdings
        :return: a set of pbks
        """
        raise NotImplementedError("Your agent must implement this method.")

    def get_proposals(self, good_pbks: List[str], current_holdings: List[int], utility_params: List[float], tx_fee: float, is_seller: bool, world_state: Optional[WorldState]) -> List[Description]:
        """
        To generate a proposals from the seller/buyer.

        :param good_pbks: a list of good pbks
        :param current_holdings: a list of current good holdings
        :param utility_params: a list of utility params
        :param tx_fee: the transaction fee
        :param is_seller: Boolean indicating the role of the agent

        :return: a list of proposals in Description form
        """
        raise NotImplementedError("Your agent must implement this method.")


def main():
    """Run the script."""
    args = parse_arguments()

    if args.gui:
        dashboard = AgentDashboard(agent_name=args.name, env_name=args.name)
    else:
        dashboard = None

    strategy = MyStrategy(register_as=RegisterAs(args.register_as), search_for=SearchFor(args.search_for), is_world_modeling=args.is_world_modeling)
    agent = BaselineAgent(name=args.name, oef_addr=args.oef_addr, oef_port=args.oef_port, agent_timeout=args.agent_timeout, strategy=strategy,
                          max_reactions=args.max_reactions, services_interval=args.services_interval, pending_transaction_timeout=args.pending_transaction_timeout,
                          dashboard=dashboard, private_key_pem=args.private_key_pem)

    try:
        agent.start(rejoin=args.rejoin)
    finally:
        agent.stop()


if __name__ == '__main__':
    main()

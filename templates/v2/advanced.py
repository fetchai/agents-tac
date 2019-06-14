#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Template agent, to complete by the developer."""

import argparse
import logging
from typing import List, Set

from oef.schema import Description

from tac.platform.game import WorldState
from tac.agents.v2.base.strategy import Strategy, RegisterAs, SearchFor
from tac.agents.v2.examples.baseline import BaselineAgent

logger = logging.getLogger(__name__)


def parse_arguments():
    parser = argparse.ArgumentParser("my_agent", description="Launch my agent.")
    parser.add_argument("--name", default="my_agent", help="Name of the agent")
    parser.add_argument("--oef-addr", default="127.0.0.1", help="TCP/IP address of the OEF Agent")
    parser.add_argument("--oef-port", default=3333, help="TCP/IP port of the OEF Agent")
    parser.add_argument("--search-interval", type=int, default=10, help="The number of seconds to wait before doing another search.")
    parser.add_argument("--pending-transaction-timeout", type=int, default=30, help="The timeout in seconds to wait for pending transaction/negotiations.")

    return parser.parse_args()


class MyStrategy(Strategy):
    """
    My strategy implementation.
    """

    def __init__(self, register_as: RegisterAs = RegisterAs.BOTH, search_for: SearchFor = SearchFor.BOTH, is_world_modeling: bool = False):
        super().__init__(register_as, search_for, is_world_modeling)

    def supplied_good_quantities(self, current_holdings: List[int]) -> List[int]:
        """
        Generates list of quantities which are supplied.

        :param current_holdings: a list of current good holdings
        :return: a list of quantities
        """
        raise NotImplementedError("Your agent must implement this method.")

    def supplied_good_pbks(self, good_pbks: List[str], current_holdings: List[int]) -> Set[str]:
        """
        Generates set of good pbks which are supplied.

        :param good_pbks: a list of good pbks
        :param current_holdings: a list of current good holdings
        :return: a set of pbks
        """
        raise NotImplementedError("Your agent must implement this method.")

    def demanded_good_quantities(self, current_holdings: List[int]) -> List[int]:
        """
        Generates list of quantities which are demanded.

        :param current_holdings: a list of current good holdings
        :return: a list of quantities
        """
        raise NotImplementedError("Your agent must implement this method.")

    def demanded_good_pbks(self, good_pbks: List[str], current_holdings: List[int]) -> Set[str]:
        """
        Generates set of good pbks which are demanded.

        :param good_pbks: a list of good pbks
        :param current_holdings: a list of current good holdings
        :return: a set of pbks
        """
        raise NotImplementedError("Your agent must implement this method.")

    def get_proposals(self, good_pbks: List[str], current_holdings: List[int], utility_params: List[int], tx_fee: float, is_seller: bool, world_state: WorldState) -> List[Description]:
        """
        Generates proposals from the seller/buyer.

        :param good_pbks: a list of good pbks
        :param current_holdings: a list of current good holdings
        :param utility_params: a list of utility params
        :param tx_fee: the transaction fee
        :param is_seller: Boolean indicating the role of the agent

        :return: a list of proposals in Description form
        """
        raise NotImplementedError("Your agent must implement this method.")


def main():
    args = parse_arguments()

    strategy = MyStrategy(register_as=RegisterAs.BOTH, search_for=SearchFor.BOTH, is_world_modeling=False)
    agent = BaselineAgent(name=args.name, oef_addr=args.oef_addr, oef_port=args.oef_port, strategy=strategy,
                          search_interval=args.search_interval, pending_transaction_timeout=args.pending_transaction_timeout)

    try:
        agent.start()
    finally:
        agent.stop()


if __name__ == '__main__':
    main()

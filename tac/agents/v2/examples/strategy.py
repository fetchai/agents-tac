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
from typing import List, Set

from oef.schema import Description

from tac.agents.v2.base.strategy import RegisterAs, SearchFor, Strategy
from tac.helpers.misc import get_goods_quantities_description, marginal_utility
from tac.platform.game import WorldState


class BaselineStrategy(Strategy):

    def __init__(self, register_as: RegisterAs = RegisterAs.BOTH, search_for: SearchFor = SearchFor.BOTH, is_world_modeling: bool = False):
        super().__init__(register_as, search_for, is_world_modeling)

    def supplied_good_quantities(self, current_holdings: List[int]) -> List[int]:
        """
        Generate a list of quantities which are supplied.

        :param current_holdings: a list of current good holdings
        :return: a list of quantities
        """
        return [quantity - 1 for quantity in current_holdings]

    def supplied_good_pbks(self, good_pbks: List[str], current_holdings: List[int]) -> Set[str]:
        """
        Generate a set of good public keys which are supplied.

        :param good_pbks: a list of good public keys
        :param current_holdings: a list of current good holdings

        :return: a set of public keys
        """
        return {good_pbk for good_pbk, quantity in zip(good_pbks, current_holdings) if quantity > 1}

    def demanded_good_quantities(self, current_holdings: List[int]) -> List[int]:
        """
        Generate a list of quantities which are demanded.

        :param current_holdings: a list of current good holdings

        :return: a list of quantities
        """
        return [1 for _ in current_holdings]

    def demanded_good_pbks(self, good_pbks: List[str], current_holdings: List[int]) -> Set[str]:
        """
        Generate a set of good public keys which are demanded.

        :param good_pbks: a list of good public keys
        :param current_holdings: a list of current good holdings
        :return: a set of public keys
        """
        return {good_pbk for good_pbk, quantity in zip(good_pbks, current_holdings)}

    def get_proposals(self, good_pbks: List[str], current_holdings: List[int], utility_params: List[int], tx_fee: float, is_seller: bool, world_state: WorldState) -> List[Description]:
        """
        Generate a proposals from the seller/buyer.

        :param good_pbks: a list of good public keys
        :param current_holdings: a list of current good holdings
        :param utility_params: a list of utility params
        :param tx_fee: the transaction fee
        :param is_seller: Boolean indicating the role of the agent

        :return: a list of proposals in Description form
        """
        quantities = self.supplied_good_quantities(current_holdings) if is_seller else self.demanded_good_quantities(current_holdings)
        share_of_tx_fee = round(tx_fee / 2.0, 2)
        rounding_adjustment = 0.01
        proposals = []
        for good_id, good_pbk in zip(range(len(quantities)), good_pbks):
            if is_seller and quantities[good_id] == 0: continue
            proposal = [0] * len(quantities)
            proposal[good_id] = 1
            desc = get_goods_quantities_description(good_pbks, proposal, is_supply=is_seller)
            delta_holdings = [i * -1 for i in proposal] if is_seller else proposal
            switch = -1 if is_seller else 1
            marginal_utility_from_delta_holdings = marginal_utility(utility_params, current_holdings, delta_holdings) * switch
            if self.is_world_modeling:
                desc.values["price"] = world_state.expected_price(good_pbk, round(marginal_utility_from_delta_holdings, 2), is_seller, share_of_tx_fee)
            else:
                if is_seller:
                    desc.values["price"] = round(marginal_utility_from_delta_holdings, 2) + share_of_tx_fee + rounding_adjustment
                else:
                    desc.values["price"] = round(marginal_utility_from_delta_holdings, 2) - share_of_tx_fee - rounding_adjustment
            proposals.append(desc)
        return proposals

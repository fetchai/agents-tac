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
import copy
from typing import List, Set

from oef.schema import Description

from tac.platform.game import WorldState
from tac.helpers.misc import get_goods_quantities_description, marginal_utility


class BaselineStrategy:

    def supplied_good_quantities(current_holdings: List[int]) -> List[int]:
        """
        Generates list of quantities which are supplied.

        :param current_holdings: a list of current good holdings
        :return: a list of quantities
        """
        return [quantity - 1 for quantity in current_holdings]

    def supplied_good_pbks(good_pbks: List[str], current_holdings: List[int]) -> Set[str]:
        """
        Generates set of good pbks which are supplied.

        :param good_pbks: a list of good pbks
        :param current_holdings: a list of current good holdings
        :return: a set of pbks
        """
        return {good_pbk for good_pbk, quantity in zip(good_pbks, current_holdings) if quantity > 1}

    def demanded_good_quantities(current_holdings: List[int]) -> List[int]:
        """
        Generates list of quantities which are demanded.

        :param current_holdings: a list of current good holdings
        :return: a list of quantities
        """
        return [1 for _ in current_holdings]

    def demanded_good_pbks(good_pbks: List[str], current_holdings: List[int]) -> Set[str]:
        """
        Generates set of good pbks which are demanded.

        :param good_pbks: a list of good pbks
        :param current_holdings: a list of current good holdings
        :return: a set of pbks
        """
        return {good_pbk for good_pbk, quantity in zip(good_pbks, current_holdings)}

    def get_proposals(good_pbks: List[str], current_holdings: List[int], utility_params: List[int], tx_fee: float, is_seller: bool, is_world_modeling: bool, world_state: WorldState) -> List[Description]:
        """
        Generates proposals from the seller/buyer.

        :param good_pbks: a list of good pbks
        :param current_holdings: a list of current good holdings
        :param utility_params: a list of utility params
        :param tx_fee: the transaction fee
        :param is_seller: Boolean indicating the role of the agent

        :return: a list of proposals in Description form
        """
        quantities = BaselineStrategy.supplied_good_quantities(current_holdings) if is_seller else BaselineStrategy.demanded_good_quantities(current_holdings)
        proposals = []
        zeroslist = [0] * len(quantities)
        rounding_adjustment = 0.01
        for good_id, good_pbk in zip(range(len(quantities)), good_pbks):
            if is_seller and quantities[good_id] == 0: continue
            lis = copy.deepcopy(zeroslist)
            lis[good_id] = 1
            desc = get_goods_quantities_description(good_pbks, lis, is_supply=is_seller)
            delta_holdings = [i * -1 for i in lis] if is_seller else lis
            switch = -1 if is_seller else 1
            marginal_utility_from_single_good = marginal_utility(utility_params, current_holdings, delta_holdings) * switch
            share_of_tx_fee = round(tx_fee / 2.0, 2)
            if is_world_modeling:
                desc.values["price"] = world_state.expected_price(good_pbk, round(marginal_utility_from_single_good, 2), is_seller, share_of_tx_fee)
            else:
                if is_seller:
                    desc.values["price"] = round(marginal_utility_from_single_good, 2) + share_of_tx_fee + rounding_adjustment
                else:
                    desc.values["price"] = round(marginal_utility_from_single_good, 2) - share_of_tx_fee - rounding_adjustment
            proposals.append(desc)
        return proposals

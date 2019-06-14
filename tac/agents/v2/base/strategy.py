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
from abc import abstractmethod
from typing import List, Set, Optional

from oef.schema import Description

from tac.platform.game import WorldState


class Strategy:

    def __init__(self, register_as: str = 'both', search_for: str = 'both', is_world_modeling: bool = False):
        self._register_as = register_as
        self._search_for = search_for
        self._is_world_modeling = is_world_modeling

    @property
    def is_world_modeling(self) -> bool:
        return self._is_world_modeling

    @property
    def is_registering_as_seller(self):
        return self._register_as == 'seller' or self._register_as == 'both'

    @property
    def is_searching_for_sellers(self):
        return self._search_for == 'sellers' or self._search_for == 'both'

    @property
    def is_registering_as_buyer(self):
        return self._register_as == 'buyer' or self._register_as == 'both'

    @property
    def is_searching_for_buyers(self):
        return self._search_for == 'buyers' or self._search_for == 'both'

    @abstractmethod
    def supplied_good_quantities(self, current_holdings: List[int]) -> List[int]:
        """
        Generates list of quantities which are supplied.

        :param current_holdings: a list of current good holdings
        :return: a list of quantities
        """

    @abstractmethod
    def supplied_good_pbks(self, good_pbks: List[str], current_holdings: List[int]) -> Set[str]:
        """
        Generates set of good pbks which are supplied.

        :param good_pbks: a list of good pbks
        :param current_holdings: a list of current good holdings
        :return: a set of pbks
        """

    @abstractmethod
    def demanded_good_quantities(self, current_holdings: List[int]) -> List[int]:
        """
        Generates list of quantities which are demanded.

        :param current_holdings: a list of current good holdings
        :return: a list of quantities
        """

    @abstractmethod
    def demanded_good_pbks(self, good_pbks: List[str], current_holdings: List[int]) -> Set[str]:
        """
        Generates set of good pbks which are demanded.

        :param good_pbks: a list of good pbks
        :param current_holdings: a list of current good holdings
        :return: a set of pbks
        """

    @abstractmethod
    def get_proposals(self, good_pbks: List[str], current_holdings: List[int], utility_params: List[float],
                      tx_fee: float, is_seller: bool, world_state: Optional[WorldState]) -> List[Description]:
        """
        Generates proposals from the seller/buyer.

        :param good_pbks: a list of good pbks
        :param current_holdings: a list of current good holdings
        :param utility_params: a list of utility params
        :param tx_fee: the transaction fee
        :param is_seller: Boolean indicating the role of the agent
        :param world_state: the world state modelled by the agent

        :return: a list of proposals in Description form
        """

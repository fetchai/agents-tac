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
from enum import Enum
from typing import List, Set, Optional

from oef.schema import Description

from tac.platform.game import WorldState


class RegisterAs(Enum):
    SELLER = 'seller'
    BUYER = 'buyer'
    BOTH = 'both'


class SearchFor(Enum):
    SELLER = 'sellers'
    BUYER = 'buyers'
    BOTH = 'both'


class Strategy:

    def __init__(self, register_as: RegisterAs, search_for: SearchFor, is_world_modeling: bool = False):
        """
        Initializes the strategy

        :param register_as: determines whether the agent registers as seller, buyer or both
        :param search_for: determines whether the agent searches for sellers, buyers or both
        :param is_world_modeling: determines whether the agent has a model of the world
        """
        self._register_as = register_as
        self._search_for = search_for
        self._is_world_modeling = is_world_modeling

    @property
    def is_world_modeling(self) -> bool:
        return self._is_world_modeling

    @property
    def is_registering_as_seller(self) -> bool:
        return self._register_as == RegisterAs.SELLER or self._register_as == RegisterAs.BUYER

    @property
    def is_searching_for_sellers(self) -> bool:
        return self._search_for == SearchFor.SELLER or self._search_for == SearchFor.BOTH

    @property
    def is_registering_as_buyer(self) -> bool:
        return self._register_as == RegisterAs.BUYER or self._register_as == RegisterAs.BOTH

    @property
    def is_searching_for_buyers(self) -> bool:
        return self._search_for == SearchFor.BUYER or self._search_for == SearchFor.BOTH

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
    def get_proposals(self, good_pbks: List[str], current_holdings: List[int], utility_params: List[float], tx_fee: float, is_seller: bool, world_state: Optional[WorldState]) -> List[Description]:
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

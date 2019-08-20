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

"""This module contains the abstract class defining an agent's strategy for the TAC."""

from abc import abstractmethod
from enum import Enum
from typing import List, Set, Optional

from oef.schema import Description

from tac.agents.participant.v1.base.states import WorldState


class RegisterAs(Enum):
    """This class defines the service registration options."""

    SELLER = 'seller'
    BUYER = 'buyer'
    BOTH = 'both'


class SearchFor(Enum):
    """This class defines the service search options."""

    SELLERS = 'sellers'
    BUYERS = 'buyers'
    BOTH = 'both'


class Strategy:
    """This class defines an abstract strategy for the agent."""

    def __init__(self, register_as: RegisterAs = RegisterAs.BOTH, search_for: SearchFor = SearchFor.BOTH, is_world_modeling: bool = False) -> None:
        """
        Initialize the strategy of the agent.

        :param register_as: determines whether the agent registers as seller, buyer or both
        :param search_for: determines whether the agent searches for sellers, buyers or both
        :param is_world_modeling: determines whether the agent has a model of the world

        :return: None
        """
        self._register_as = register_as
        self._search_for = search_for
        self._is_world_modeling = is_world_modeling

    @property
    def is_world_modeling(self) -> bool:
        """Check if the world is modeled by the agent."""
        return self._is_world_modeling

    @property
    def is_registering_as_seller(self) -> bool:
        """Check if the agent registers as a seller on the OEF."""
        return self._register_as == RegisterAs.SELLER or self._register_as == RegisterAs.BUYER

    @property
    def is_searching_for_sellers(self) -> bool:
        """Check if the agent searches for sellers on the OEF."""
        return self._search_for == SearchFor.SELLERS or self._search_for == SearchFor.BOTH

    @property
    def is_registering_as_buyer(self) -> bool:
        """Check if the agent registers as a buyer on the OEF."""
        return self._register_as == RegisterAs.BUYER or self._register_as == RegisterAs.BOTH

    @property
    def is_searching_for_buyers(self) -> bool:
        """Check if the agent searches for buyers on the OEF."""
        return self._search_for == SearchFor.BUYERS or self._search_for == SearchFor.BOTH

    @abstractmethod
    def supplied_good_quantities(self, current_holdings: List[int]) -> List[int]:
        """
        Generate a list of quantities which are supplied by the agent.

        :param current_holdings: a list of current good holdings

        :return: a list of quantities
        """

    @abstractmethod
    def supplied_good_pbks(self, good_pbks: List[str], current_holdings: List[int]) -> Set[str]:
        """
        Generate a set of good public keys which are supplied by the agent.

        :param good_pbks: a list of good public keys
        :param current_holdings: a list of current good holdings

        :return: a set of public keys
        """

    @abstractmethod
    def demanded_good_quantities(self, current_holdings: List[int]) -> List[int]:
        """
        Generate a list of quantities which are demanded by the agent.

        :param current_holdings: a list of current good holdings

        :return: a list of quantities
        """

    @abstractmethod
    def demanded_good_pbks(self, good_pbks: List[str], current_holdings: List[int]) -> Set[str]:
        """
        Generate a set of good public keys which are demanded by the agent.

        :param good_pbks: a list of good public keys
        :param current_holdings: a list of current good holdings

        :return: a set of public keys
        """

    @abstractmethod
    def get_proposals(self, good_pbks: List[str], current_holdings: List[int], utility_params: List[float],
                      tx_fee: float, is_seller: bool, world_state: Optional[WorldState]) -> List[Description]:
        """
        Generate proposals from the agent in the role of seller/buyer.

        :param good_pbks: a list of good public keys
        :param current_holdings: a list of current good holdings
        :param utility_params: a list of utility params
        :param tx_fee: the transaction fee
        :param is_seller: Boolean indicating the role of the agent
        :param world_state: the world state modelled by the agent

        :return: a list of proposals in Description form
        """

    def is_acceptable_proposal(self, proposal_delta_score: float) -> bool:
        """
        Determine whether a proposal is acceptable to the agent.

        :param proposal_delta_score: the difference in score the proposal causes

        :return: a boolean indicating whether the proposal is acceptable or not
        """
        result = proposal_delta_score >= 0
        return result

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

"""
This module contains the classes which define the states of an agent.

- AgentState: a class to hold the current state of an agent.
- GoodState: a class to hold the current state of a good.
- WorldState represent the state of the world from the perspective of the agent.
"""

import copy
import pprint
from typing import Dict, List

from tac.aea.state.base import AgentState as BaseAgentState
from tac.aea.state.base import WorldState as BaseWorldState
from tac.agents.participant.base.price_model import GoodPriceModel
from tac.platform.game.helpers import logarithmic_utility
from tac.platform.protocol import Transaction

Endowment = List[int]  # an element e_j is the endowment of good j.
UtilityParams = List[float]  # an element u_j is the utility value of good j.


class AgentState(BaseAgentState):
    """Represent the state of an agent during the game."""

    def __init__(self, money: float, endowment: Endowment, utility_params: UtilityParams):
        """
        Instantiate an agent state object.

        :param money: the money of the agent in this state.
        :param endowment: the endowment for every good.
        :param utility_params: the utility params for every good.
        """
        super().__init__()
        assert len(endowment) == len(utility_params)
        self.balance = money
        self._utility_params = copy.copy(utility_params)
        self._current_holdings = copy.copy(endowment)

    @property
    def current_holdings(self):
        """Get current holding of each good."""
        return copy.copy(self._current_holdings)

    @property
    def utility_params(self) -> UtilityParams:
        """Get utility parameter for each good."""
        return copy.copy(self._utility_params)

    def get_score(self) -> float:
        """
        Compute the score of the current state.

        The score is computed as the sum of all the utilities for the good holdings
        with positive quantity plus the money left.
        :return: the score.
        """
        goods_score = logarithmic_utility(self.utility_params, self.current_holdings)
        money_score = self.balance
        score = goods_score + money_score
        return score

    def get_score_diff_from_transaction(self, tx: Transaction, tx_fee: float) -> float:
        """
        Simulate a transaction and get the resulting score (taking into account the fee).

        :param tx: a transaction object.
        :return: the score.
        """
        current_score = self.get_score()
        new_state = self.apply([tx], tx_fee)
        new_score = new_state.get_score()
        return new_score - current_score

    def check_transaction_is_consistent(self, tx: Transaction, tx_fee: float) -> bool:
        """
        Check if the transaction is consistent.

        E.g. check that the agent state has enough money if it is a buyer
        or enough holdings if it is a seller.
        :return: True if the transaction is legal wrt the current state, false otherwise.
        """
        share_of_tx_fee = round(tx_fee / 2.0, 2)
        if tx.is_sender_buyer:
            # check if we have the money.
            result = self.balance >= tx.amount + share_of_tx_fee
        else:
            # check if we have the goods.
            result = True
            for good_id, quantity in enumerate(tx.quantities_by_good_pbk.values()):
                result = result and (self._current_holdings[good_id] >= quantity)
        return result

    def apply(self, transactions: List[Transaction], tx_fee: float) -> 'AgentState':
        """
        Apply a list of transactions to the current state.

        :param transactions: the sequence of transaction.
        :return: the final state.
        """
        new_state = copy.copy(self)
        for tx in transactions:
            new_state.update(tx, tx_fee)

        return new_state

    def update(self, tx: Transaction, tx_fee: float) -> None:
        """
        Update the agent state from a transaction.

        :param tx: the transaction.
        :param tx_fee: the transaction fee.
        :return: None
        """
        share_of_tx_fee = round(tx_fee / 2.0, 2)
        if tx.is_sender_buyer:
            diff = tx.amount + share_of_tx_fee
            self.balance -= diff
        else:
            diff = tx.amount - share_of_tx_fee
            self.balance += diff

        for good_id, quantity in enumerate(tx.quantities_by_good_pbk.values()):
            quantity_delta = quantity if tx.is_sender_buyer else -quantity
            self._current_holdings[good_id] += quantity_delta

    def __copy__(self):
        """Copy the object."""
        return AgentState(self.balance, self.current_holdings, self.utility_params)

    def __str__(self):
        """From object to string."""
        return "AgentState{}".format(pprint.pformat({
            "money": self.balance,
            "utility_params": self.utility_params,
            "current_holdings": self._current_holdings
        }))

    def __eq__(self, other) -> bool:
        """Compare equality of two instances of the class."""
        return isinstance(other, AgentState) and \
            self.balance == other.balance and \
            self.utility_params == other.utility_params and \
            self._current_holdings == other._current_holdings


class WorldState(BaseWorldState):
    """Represent the state of the world from the perspective of the agent."""

    def __init__(self, opponent_pbks: List[str],
                 good_pbks: List[str],
                 initial_agent_state: AgentState) -> None:
        """
        Instantiate an agent state object.

        :param opponent_pbks: the public keys of the opponents
        :param good_pbks: the public keys of the goods
        :param agent_state: the initial state of the agent
        :return: None
        """
        super().__init__()
        self.opponent_states = dict(
            (agent_pbk,
                AgentState(
                    self._expected_initial_money_amount(initial_agent_state.balance),
                    self._expected_good_endowments(initial_agent_state.current_holdings),
                    self._expected_utility_params(initial_agent_state.utility_params)
                ))
            for agent_pbk in opponent_pbks)  # type: Dict[str, AgentState]

        self.good_price_models = dict(
            (good_pbk,
                GoodPriceModel())
            for good_pbk in good_pbks)

    def update_on_cfp(self, query) -> None:
        """Update the world state when a new cfp is received."""
        pass

    def update_on_proposal(self, proposal) -> None:
        """Update the world state when a new proposal is received."""
        pass

    def update_on_declined_propose(self, transaction: Transaction) -> None:
        """
        Update the world state when a transaction (propose) is rejected.

        :param transaction: the transaction
        :return: None
        """
        self._from_transaction_update_price(transaction, is_accepted=False)

    def _from_transaction_update_price(self, transaction: Transaction, is_accepted: bool) -> None:
        """
        Update the good price model based on a transaction.

        :param transaction: the transaction
        :param is_accepted: whether the transaction is accepted or not
        :return: None
        """
        good_pbks = []  # type: List[str]
        for good_pbk, quantity in transaction.quantities_by_good_pbk.items():
            if quantity > 0:
                good_pbks += [good_pbk] * quantity
        price = transaction.amount
        price = price / len(good_pbks)
        for good_pbk in list(set(good_pbks)):
            self._update_price(good_pbk, price, is_accepted=is_accepted)

    def update_on_initial_accept(self, transaction: Transaction) -> None:
        """
        Update the world state when a proposal is accepted.

        :param transaction: the transaction
        :return: None
        """
        self._from_transaction_update_price(transaction, is_accepted=True)

    def _expected_initial_money_amount(self, initial_money_amount: float) -> float:
        """
        Compute expectation of the initial_money_amount of an opponent.

        :param initial_money_amount: the initial amount of money of the agent.
        :return: the expected initial money amount of the opponent
        """
        # Naiive expectation
        expected_initial_money_amount = initial_money_amount
        return expected_initial_money_amount

    def _expected_good_endowments(self, good_endowment: Endowment) -> Endowment:
        """
        Compute expectation of the good endowment of an opponent.

        :param good_endowment: the good_endowment of the agent.
        :return: the expected good endowment of the opponent
        """
        # Naiive expectation
        expected_good_endowment = good_endowment
        return expected_good_endowment

    def _expected_utility_params(self, utility_params: UtilityParams) -> UtilityParams:
        """
        Compute expectation of the utility params of an opponent.

        :param utility_params: the utility_params of the agent.
        :return: the expected utility params of the opponent
        """
        # Naiive expectation
        expected_utility_params = utility_params
        return expected_utility_params

    def expected_price(self, good_pbk: str, marginal_utility: float, is_seller: bool, share_of_tx_fee: float) -> float:
        """
        Compute expectation of the price for the good given a constraint.

        :param good_pbk: the pbk of the good
        :param marginal_utility: the marginal_utility from the good
        :param is_seller: whether the agent is a seller or buyer
        :param share_of_tx_fee: the share of the tx fee the agent pays
        :return: the expected price
        """
        constraint = round(marginal_utility + share_of_tx_fee, 1) if is_seller else round(marginal_utility - share_of_tx_fee, 1)
        good_price_model = self.good_price_models[good_pbk]
        expected_price = good_price_model.get_price_expectation(constraint, is_seller)
        return expected_price

    def _update_price(self, good_pbk: str, price: float, is_accepted: bool) -> None:
        """
        Update the price for the good based on an outcome.

        :param good_pbk: the pbk of the good
        :param price: the price to which the outcome relates
        :param is_accepted: boolean indicating the outcome
        :return: None
        """
        price = round(price, 1)
        good_price_model = self.good_price_models[good_pbk]
        good_price_model.update(is_accepted, price)

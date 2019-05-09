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

"""This module contains all the classes to represent the TAC game.

Classes:

- GameConfiguration: a class to hold the initial configuration of a game. Immutable.
- Game: the class that manages an instance of a game (e.g. validate and settling transactions).
- AgentState: a class to hold the current state of an agent.
- GameTransaction: a class that keeps information about a transaction in the game.

"""

import copy
import datetime
import logging
import pprint
from typing import List, Dict, Any, Optional

from tac.helpers.misc import generate_initial_money_amounts, generate_endowments, generate_utilities, from_iso_format, \
    logarithmic_utility
from tac.protocol import Transaction

Endowment = List[int]  # an element e_j is the endowment of good j.
Utilities = List[float]  # an element u_j is the utility value of good j.

logger = logging.getLogger(__name__)


class GameConfiguration:

    def __init__(self, initial_money_amounts: List[int],
                 endowments: List[Endowment],
                 utilities: List[Utilities],
                 fee: int,
                 agent_labels: Optional[List[str]] = None):
        """
        Initialize a game configuration.
        :param initial_money_amounts: the initial amount of money for every agent.
        :param endowments: the endowments of the agents. A matrix where the first index is the agent id
                            and the second index is the good id. A generic element e_ij at row i and column j is
                            an integer that denotes the endowment of good j for agent i.
        :param utilities: the utilities representing the preferences of the agents. A matrix where the first
                            index is the agent id and the second index is the good id. A generic element e_ij
                            at row i and column j is an integer that denotes the utility of good j for agent i.
        :param fee: the fee for a transaction.
        :param agent_labels: a list of participant labels (as strings). If None, generate a default list of labels.
        """

        self._initial_money_amounts = initial_money_amounts
        self._endowments = endowments
        self._utilities = utilities
        self._fee = fee

        self._agent_labels = agent_labels if agent_labels is not None else self._generate_ids(self.nb_agents, 'agent')

        self._from_agent_pbk_to_agent_id = dict(map(reversed, enumerate(self.agent_labels)))

        self._check_consistency()

    @property
    def initial_money_amounts(self) -> List[int]:
        return self._initial_money_amounts

    @property
    def endowments(self) -> List[Endowment]:
        return self._endowments

    @property
    def utilities(self) -> List[Utilities]:
        return self._utilities

    @property
    def fee(self) -> int:
        return self._fee

    @property
    def nb_agents(self) -> int:
        return len(self.endowments)

    @property
    def nb_goods(self) -> int:
        return len(self.endowments[0])

    @property
    def agent_labels(self) -> List[str]:
        return self._agent_labels

    @property
    def good_labels(self) -> List[str]:
        return self._generate_ids(len(self.endowments[0]), 'good')

    def _generate_ids(self, nb: int, thing_name: str) -> List[str]:
        """
        Generate ids for things.
        :param nb_agents: the number of things.
        :return: a list of labels.
        """
        return [thing_name + "_{:02}".format(i) for i in range(nb)]

    def agent_id_from_label(self, agent_label: str) -> int:
        """
        From the label of an agent to his id.
        :param agent_label: the label of the agent.
        :return: the integer identifier.
        """
        return self._from_agent_pbk_to_agent_id[agent_label]

    def _check_consistency(self):
        """
        Check the consistency of the game configuration.
        :return: None
        :raises: AssertionError: if some constraint is not satisfied.
        """

        assert all(money >= 0 for money in self.initial_money_amounts) > 0, "All the money must be a non-negative value."
        assert all(e >= 0 for row in self.endowments for e in row), "Endowments must be non-negative."
        assert all(e >= 0 for row in self.utilities for e in row), "Utilities must be non-negative."
        assert self.fee >= 0, "Fee must be non-negative."

        # checks that the data structure have information about the right number of agents
        assert self.nb_agents > 1
        assert self.nb_agents == len(self.initial_money_amounts)
        assert self.nb_agents == len(self.endowments)
        assert self.nb_agents == len(self.utilities)
        assert self.nb_agents == len(self.agent_labels)

        # checks that all the rows have the same dimensions.
        assert self.nb_goods > 0
        assert all(self.nb_goods == len(row) for row in self.endowments)
        assert all(self.nb_goods == len(row) for row in self.utilities)

        assert len(set(self.agent_labels)) == self.nb_agents, "Labels must be unique."

    def to_dict(self) -> Dict[str, Any]:
        return {
            "initial_money_amounts": self.initial_money_amounts,
            "endowments": self.endowments,
            "utilities": self.utilities,
            "fee": self.fee,
            "agent_labels": self.agent_labels
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'GameConfiguration':
        """Instantiate an object from the dictionary."""

        obj = cls(
            d["initial_money_amounts"],
            d["endowments"],
            d["utilities"],
            d["fee"],
            d["agent_labels"]
        )
        return obj

    def __eq__(self, other):
        return isinstance(other, GameConfiguration) and \
            self.initial_money_amounts == other.initial_money_amounts and \
            self.endowments == other.endowments and \
            self.utilities == other.utilities and \
            self.fee == other.fee


class Game:
    """
    >>> money_amounts = [20, 20, 20]
    >>> endowments = [
    ... [1, 1, 1],
    ... [2, 1, 1],
    ... [1, 1, 2]]
    >>> utilities = [
    ... [20.0, 40.0, 40.0],
    ... [10.0, 50.0, 40.0],
    ... [40.0, 30.0, 30.0]]
    >>> fee = 1
    >>> game_configuration = GameConfiguration(
    ...     money_amounts,
    ...     endowments,
    ...     utilities,
    ...     fee
    ... )
    >>> game = Game(game_configuration)

    Get the scores:
    >>> game.get_scores()
    [20.0, 33.86294361119891, 61.58883083359672]
    """

    def __init__(self, configuration: GameConfiguration):
        """
        Initialize a game.
        :param configuration: the game configuration.
        """
        self.configuration = configuration
        self.transactions = []  # type: List[GameTransaction]

        # instantiate the agent state for every agent.
        self.agent_states = [
            AgentState(
                configuration.initial_money_amounts[i],
                configuration.endowments[i],
                configuration.utilities[i],
                configuration.fee
            )
            for i in range(configuration.nb_agents)]  # type: List[AgentState]

        # instantiate the initial agent state for every agent.
        self.initial_agent_states = [
            AgentState(
                configuration.initial_money_amounts[i],
                configuration.endowments[i],
                configuration.utilities[i],
                configuration.fee
            )
            for i in range(configuration.nb_agents)]  # type: List[AgentState]

        # instantiate the good state for every good.
        self.good_states = [
            GoodState(
                0.0,
                configuration.fee
            )
            for i in range(configuration.nb_goods)]  # type: List[GoodState]

    @staticmethod
    def generate_game(nb_agents: int,
                      nb_goods: int,
                      money_endowment: int,
                      fee: int,
                      lower_bound_factor: int,
                      upper_bound_factor: int,
                      agent_ids: List[str] = None) -> 'Game':
        """
        Generate a game, the endowments and the utilites.
        :param nb_agents: the number of agents.
        :param nb_goods: the number of goods.
        :param money_endowment: the initial amount of money for every agent.
        :param fee: the fee to pay per transaction.
        :param lower_bound_factor: the lower bound of a uniform distribution.
        :param upper_bound_factor: the upper bound of a uniform distribution
        :param agent_ids: the labels for the agents.
        :return: a game.
        """
        initial_money_amounts = generate_initial_money_amounts(nb_agents, money_endowment)
        endowments = generate_endowments(nb_goods, nb_agents, lower_bound_factor, upper_bound_factor)
        utilities = generate_utilities(nb_agents, nb_goods)
        configuration = GameConfiguration(initial_money_amounts, endowments, utilities, fee, agent_ids)
        return Game(configuration)

    def get_initial_scores(self) -> List[float]:
        """Get the initial scores for every agent."""
        return [agent_state.get_score() for agent_state in self.initial_agent_states]

    def get_scores(self) -> List[float]:
        """Get the current scores for every agent."""
        return [agent_state.get_score() for agent_state in self.agent_states]

    def agent_id_from_label(self, agent_label: str) -> int:
        """
        Get agent id from label.
        :param agent_label: the label for the agent.
        :return: the agent id associated with the label.
        """
        return self.configuration.agent_id_from_label(agent_label)

    def get_agent_state_from_agent_label(self, agent_label: str) -> 'AgentState':
        """
        Get agent state from agent label.
        :param agent_label: the agent's label.
        :return: the agent state of the agent.
        """
        return self.agent_states[self.configuration.agent_id_from_label(agent_label)]

    def is_transaction_valid(self, tx: 'GameTransaction') -> bool:
        """
        Check whether the transaction is valid given the state of the game.
        :param tx: the game transaction.
        :return: True if the transaction is valid, False otherwise.
        :raises: AssertionError: if the data in the transaction are not allowed (e.g. negative amount).
        """

        # check if the buyer has enough balance to pay the transaction.
        if self.agent_states[tx.buyer_id].balance < tx.amount + self.configuration.fee:
            return False

        # check if we have enough instances of goods, for every good involved in the transaction.
        seller_holdings = self.agent_states[tx.seller_id].current_holdings
        for good_id, bought_quantity in tx.quantities_by_good_id.items():
            if seller_holdings[good_id] < bought_quantity:
                return False

        return True

    def settle_transaction(self, tx: 'GameTransaction') -> None:
        """
        Settle a valid transaction.

        >>> game = Game(GameConfiguration(
        ... initial_money_amounts = [20, 20],
        ... endowments = [[0, 0], [1, 1]],
        ... utilities = [[80.0, 20.0], [10.0, 90.0]],
        ... fee = 0))
        >>> agent_state_1 = game.agent_states[0] # agent state of player 1
        >>> agent_state_2 = game.agent_states[1] # agent state of player 2
        >>> agent_state_1.balance, agent_state_1.current_holdings
        (20, [0, 0])
        >>> agent_state_2.balance, agent_state_2.current_holdings
        (20, [1, 1])
        >>> game.settle_transaction(GameTransaction(0, 1, 20, {0: 1, 1: 1}))
        >>> agent_state_1.balance, agent_state_1.current_holdings
        (0, [1, 1])
        >>> agent_state_2.balance, agent_state_2.current_holdings
        (40, [0, 0])

        :param tx: the game transaction.
        :return: None
        :raises: AssertionError if the transaction is not valid.
        """
        assert self.is_transaction_valid(tx)
        self.transactions.append(tx)
        buyer_state = self.agent_states[tx.buyer_id]
        seller_state = self.agent_states[tx.seller_id]

        nb_instances_traded = sum(tx.quantities_by_good_id.values())

        # update holdings and prices
        for good_id, quantity in tx.quantities_by_good_id.items():
            buyer_state._current_holdings[good_id] += quantity
            seller_state._current_holdings[good_id] -= quantity
            if quantity > 0:
                price = (tx.amount - self.configuration.fee) / nb_instances_traded
                good_state = self.good_states[good_id]
                good_state.price = price

        # update balances and charge fee to buyer
        buyer_state.balance -= tx.amount + self.configuration.fee
        seller_state.balance += tx.amount

    def get_holdings_matrix(self) -> List[Endowment]:
        """
        Get the holdings matrix of shape (nb_agents, nb_goods).
        :return: the holdings matrix.
        """
        result = list(map(lambda state: state.current_holdings, self.agent_states))
        return result

    def get_balances(self) -> List[float]:
        """Get the current balances."""
        result = list(map(lambda state: state.balance, self.agent_states))
        return result

    def get_prices(self) -> List[float]:
        """Get the current prices."""
        result = list(map(lambda state: state.price, self.good_states))
        return result

    def get_holdings_summary(self) -> str:
        """
        Get holdings summary.

        >>> money_amounts = [20, 20, 20]
        >>> endowment = [
        ... [1, 1, 0],
        ... [1, 0, 0],
        ... [0, 1, 2]]
        >>> utilities = [
        ... [20.0, 20.0, 60.0],
        ... [10.0, 50.0, 40.0],
        ... [30.0, 20.0, 50.0]]
        >>> fee = 1
        >>> game_configuration = GameConfiguration(
        ... money_amounts,
        ... endowment,
        ... utilities,
        ... fee)
        >>> game = Game(game_configuration)
        >>> print(game.get_holdings_summary(), end="")
        00 [1, 1, 0]
        01 [1, 0, 0]
        02 [0, 1, 2]

        :return: a string representing the holdings for every agent.
        """
        result = ""
        for i, agent_state in enumerate(self.agent_states):
            result = result + "{:02d}".format(i) + " " + str(agent_state._current_holdings) + "\n"
        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "configuration": self.configuration.to_dict(),
            "transactions": [t.to_dict() for t in self.transactions]
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'Game':
        configuration = GameConfiguration.from_dict(d["configuration"])

        game = Game(configuration)
        for tx_dict in d["transactions"]:
            tx = GameTransaction.from_dict(tx_dict)
            game.settle_transaction(tx)

        return game

    def __eq__(self, other):
        return isinstance(other, Game) and \
            self.configuration == other.configuration and \
            self.transactions == other.transactions


class AgentState:
    """Represent the state of an agent during the game."""

    def __init__(self, money: int, endowment: Endowment, utilities: Utilities, tx_fee: int):
        """
        Instantiate an agent state object.

        :param money: the money of the agent in this state.
        :param endowment: the endowment for every good.
        :param utilities: the utility values for every good.
        :param tx_fee: the fee of a transaction (i.e. state transition)
        """
        assert len(endowment) == len(utilities)
        self.balance = money
        self._utilities = copy.copy(utilities)
        self._current_holdings = copy.copy(endowment)

        self.tx_fee = tx_fee
        self.nb_goods = len(utilities)

    @property
    def current_holdings(self):
        return copy.copy(self._current_holdings)

    @property
    def utilities(self) -> Utilities:
        return copy.copy(self._utilities)

    def get_score(self) -> float:
        """
        Compute the score of the current state.
        The score is computed as the sum of all the utilities for the good holdings
        with positive quantity plus the money left.
        :return: the score.
        """
        goods_score = logarithmic_utility(self.utilities, self.current_holdings)
        money_score = self.balance
        score = goods_score + money_score
        return score

    def get_score_diff_from_transaction(self, tx: Transaction) -> float:
        """
        Simulate a transaction and get the resulting score (taking into account the fee)
        :param tx: a transaction object.
        :return: the score.
        """
        current_score = self.get_score()
        new_state = self.apply([tx])
        new_score = new_state.get_score()
        return new_score - current_score

    def restore(self, tx: Transaction) -> None:
        """
        Apply the transaction to the state, but backwards.
        :param tx: the transaction.
        :return: None
        """
        switch = 1 if tx.buyer else -1

        fee = self.tx_fee if not tx.buyer else 0
        self.balance += switch * (tx.amount + fee)
        for good_id, quantity in tx.quantities_by_good_id.items():
            self._current_holdings[good_id] += -switch * quantity

    def check_transaction_is_consistent(self, tx: Transaction) -> bool:
        """
        Check if the transaction is consistent.  E.g. check that the agent state has enough money if it is a buyer
        or enough holdings if it is a seller.
        :return: True if the transaction is legal wrt the current state, false otherwise.
        """

        if tx.buyer:
            # check if we have the money.
            result = self.balance >= tx.amount + self.tx_fee
        else:
            # check if we have the goods.
            result = True
            for good_id, quantity in tx.quantities_by_good_id.items():
                result = result and (self._current_holdings[good_id] >= quantity)
        return result

    def apply(self, transactions: List[Transaction]) -> 'AgentState':
        """
        Apply a list of transactions to the current state.
        :param transactions: the sequence of transaction.
        :return: the final state.
        """

        new_state = copy.copy(self)
        for tx in transactions:
            new_state.update(tx)

        return new_state

    def update(self, tx: Transaction) -> None:
        """
        Update the agent state from a transaction request.
        :param tx: the transaction request message.
        :return: None
        """
        if tx.buyer:
            fees = tx.amount + self.tx_fee
            self.balance -= fees
        else:
            self.balance += tx.amount

        for good_id, quantity in tx.quantities_by_good_id.items():
            quantity_delta = quantity if tx.buyer else -quantity
            self._current_holdings[good_id] += quantity_delta

    def __copy__(self):
        return AgentState(self.balance, self.current_holdings, self.utilities, self.tx_fee)

    def __str__(self):
        return "AgentState{}".format(pprint.pformat({
            "money": self.balance,
            "utilities": self.utilities,
            "current_holdings": self._current_holdings,
            "fee": self.tx_fee
        }))

    def __eq__(self, other) -> bool:
        return isinstance(other, AgentState) and \
            self.balance == other.balance and \
            self.utilities == other.utilities and \
            self._current_holdings == other._current_holdings


class GoodState:
    """Represent the state of a good during the game."""

    def __init__(self, price: float, tx_fee: int):
        """
        Instantiate an agent state object.

        :param price: price of the good in this state.
        # :param nb_instances: the instances of this good.
        :param tx_fee: the fee of a transaction (i.e. state transition)
        """
        self.price = price
        # self.nb_instances = nb_instances
        self.tx_fee = tx_fee

    def apply(self, transactions: List[Transaction]) -> 'GoodState':
        """
        Apply a list of transactions to the current state.
        :param transactions: the sequence of transaction.
        :return: the final state.
        """

        new_state = copy.copy(self)
        for tx in transactions:
            new_state.update(tx)

        return new_state

    def update(self, tx: Transaction) -> None:
        """
        Update the good state from a transaction request.
        :param tx: the transaction request message.
        :return: None
        """
        self.price = tx.amount - self.tx_fee


class GameTransaction:
    """Represent a transaction between agents"""

    def __init__(self, buyer_id: int, seller_id: int, amount: int, quantities_by_good_id: Dict[int, int],
                 timestamp: Optional[datetime.datetime] = None):
        """
        Instantiate a game transaction object.

        :param buyer_id: the participant id of the buyer in the game.
        :param seller_id: the participant id of the seller in the game.
        :param amount: the amount transferred.
        :param quantities_by_good_id: a map from good id to the quantity transacted.
        :param timestamp: the timestamp of the transaction.
        """
        self.buyer_id = buyer_id
        self.seller_id = seller_id
        self.amount = amount
        self.quantities_by_good_id = quantities_by_good_id
        self.timestamp = datetime.datetime.now() if timestamp is None else timestamp

        self._check_consistency()

    def _check_consistency(self):
        """
        Check the consistency of the transaction parameters.
        :return: None
        :raises AssertionError if some constraint is not satisfied.
        """

        assert self.buyer_id != self.seller_id
        assert self.amount >= 0
        assert all(good_id >= 0 for good_id in self.quantities_by_good_id.keys())
        assert all(quantity >= 0 for quantity in self.quantities_by_good_id.values())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "buyer_id": self.buyer_id,
            "seller_id": self.seller_id,
            "amount": self.amount,
            "quantities_by_good_id": self.quantities_by_good_id,
            "timestamp": str(self.timestamp)
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'GameTransaction':
        # make the keys as integers
        quantities_by_good_id = {int(k): v for k, v in d["quantities_by_good_id"].items()}

        return cls(
            buyer_id=d["buyer_id"],
            seller_id=d["seller_id"],
            amount=d["amount"],
            quantities_by_good_id=quantities_by_good_id,
            timestamp=from_iso_format(d["timestamp"])
        )

    def __eq__(self, other) -> bool:
        return isinstance(other, GameTransaction) and \
            self.buyer_id == other.buyer_id and \
            self.seller_id == other.seller_id and \
            self.amount == other.amount and \
            self.quantities_by_good_id == other.quantities_by_good_id and \
            self.timestamp == other.timestamp

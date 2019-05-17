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

- GameConfiguration: a class to hold the configuration of a game. Immutable.
- GameInitialization: a class to hold the initialization of a game. Immutable.
- Game: the class that manages an instance of a game (e.g. validate and settling transactions).
- AgentState: a class to hold the current state of an agent.
- GoodState: a class to hold the current state of a good.
- GameTransaction: a class that keeps information about a transaction in the game.

"""

import copy
import datetime
import logging
import pprint
from typing import List, Dict, Any, Optional

from tac.helpers.misc import generate_initial_money_amounts, generate_endowments, generate_utility_params, from_iso_format, \
    logarithmic_utility
from tac.protocol import Transaction

Endowment = List[int]  # an element e_j is the endowment of good j.
UtilityParams = List[float]  # an element u_j is the utility value of good j.

logger = logging.getLogger(__name__)

DEFAULT_PRICE = 0.0


class GameConfiguration:

    def __init__(self,
                 nb_agents: int,
                 nb_goods: int,
                 tx_fee: float,
                 agent_pbks: List[str],
                 good_pbks: List[str]):
        """
        Configuration of a game.
        :param nb_agents: the number of agents.
        :param nb_goods: the number of goods.
        :param tx_fee: the fee for a transaction.
        :param agent_pbks: a list of agent public keys (as strings).
        :param good_pbks: a list of good public keys (as strings).
        """

        self._nb_agents = nb_agents
        self._nb_goods = nb_goods
        self._tx_fee = tx_fee
        self._agent_pbks = agent_pbks
        self._good_pbks = good_pbks

        self._check_consistency()

    @property
    def nb_agents(self) -> int:
        return self._nb_agents

    @property
    def nb_goods(self) -> int:
        return self._nb_goods

    @property
    def tx_fee(self) -> float:
        return self._tx_fee

    @property
    def agent_pbks(self) -> List[str]:
        return self._agent_pbks

    @property
    def good_pbks(self) -> List[str]:
        return self._good_pbks

    def _check_consistency(self):
        """
        Check the consistency of the game configuration.
        :return: None
        :raises: AssertionError: if some constraint is not satisfied.
        """
        assert self.tx_fee >= 0, "Tx fee must be non-negative."
        assert self.nb_agents > 1, "Must have at least two agents."
        assert self.nb_goods > 1, "Must have at least two goods."
        assert len(set(self.agent_pbks)) == self.nb_agents, "Agents' pbks must be unique."
        assert len(set(self.good_pbks)) == self.nb_goods, "Goods' pbks must be unique."

    def to_dict(self) -> Dict[str, Any]:
        """Get a dictionary from the object."""
        return {
            "nb_agents": self.nb_agents,
            "nb_goods": self.nb_goods,
            "tx_fee": self.tx_fee,
            "agent_pbks": self.agent_pbks,
            "good_pbks": self.good_pbks
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'GameConfiguration':
        """Instantiate an object from the dictionary."""
        obj = cls(
            d["nb_agents"],
            d["nb_goods"],
            d["tx_fee"],
            d["agent_pbks"],
            d["good_pbks"]
        )
        return obj

    def __eq__(self, other):
        return isinstance(other, GameConfiguration) and \
            self.nb_agents == other.nb_agents and \
            self.nb_goods == other.nb_goods and \
            self.tx_fee == other.tx_fee and \
            self.agent_pbks == other.agent_pbks and \
            self.good_pbks == other.good_pbks


class GameInitialization:

    def __init__(self,
                 initial_money_amounts: List[int],
                 endowments: List[Endowment],
                 utility_params: List[UtilityParams]):
        """
        Initialization of a game.
        :param initial_money_amounts: the initial amount of money of every agent.
        :param endowments: the endowments of the agents. A matrix where the first index is the agent id
                            and the second index is the good id. A generic element e_ij at row i and column j is
                            an integer that denotes the endowment of good j for agent i.
        :param utility_params: the utility params representing the preferences of the agents. A matrix where the first
                            index is the agent id and the second index is the good id. A generic element e_ij
                            at row i and column j is an integer that denotes the utility of good j for agent i.
        """

        self._initial_money_amounts = initial_money_amounts
        self._endowments = endowments
        self._utility_params = utility_params

        self._check_consistency()

    @property
    def initial_money_amounts(self) -> List[int]:
        return self._initial_money_amounts

    @property
    def endowments(self) -> List[Endowment]:
        return self._endowments

    @property
    def utility_params(self) -> List[UtilityParams]:
        return self._utility_params

    def _check_consistency(self):
        """
        Check the consistency of the game configuration.
        :return: None
        :raises: AssertionError: if some constraint is not satisfied.
        """

        assert all(money >= 0 for money in self.initial_money_amounts), "Money must be non-negative."
        assert all(e > 0 for row in self.endowments for e in row), "Endowments must be strictly positive."
        assert all(e > 0 for row in self.utility_params for e in row), "UtilityParams must be strictly positive."

        assert len(self.endowments) == len(self.initial_money_amounts), "Length of endowments and initial_money_amounts must be the same."
        assert len(self.endowments) == len(self.utility_params), "Length of endowments and utility_params must be the same."

        assert all(len(row_e) == len(row_u) for row_e, row_u in zip(self.endowments, self.utility_params)), "Dimensions for utility_params and endowments rows must be the same."

    def to_dict(self) -> Dict[str, Any]:
        """Get a dictionary from the object."""
        return {
            "initial_money_amounts": self.initial_money_amounts,
            "endowments": self.endowments,
            "utility_params": self.utility_params
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'GameInitialization':
        """Instantiate an object from the dictionary."""
        obj = cls(
            d["initial_money_amounts"],
            d["endowments"],
            d["utility_params"],
        )
        return obj

    def __eq__(self, other):
        return isinstance(other, GameInitialization) and \
            self.initial_money_amounts == other.initial_money_amounts and \
            self.endowments == other.endowments and \
            self.utility_params == other.utility_params


class Game:
    """
    >>> nb_agents = 3
    >>> nb_goods = 3
    >>> tx_fee = 1.0
    >>> agent_pbks = ['tac_agent_0', 'tac_agent_1', 'tac_agent_2']
    >>> good_pbks = ['tac_good_0', 'tac_good_1', 'tac_good_2']
    >>> money_amounts = [20, 20, 20]
    >>> endowments = [
    ... [1, 1, 1],
    ... [2, 1, 1],
    ... [1, 1, 2]]
    >>> utility_params = [
    ... [20.0, 40.0, 40.0],
    ... [10.0, 50.0, 40.0],
    ... [40.0, 30.0, 30.0]]
    >>> game_configuration = GameConfiguration(
    ...     nb_agents,
    ...     nb_goods,
    ...     tx_fee,
    ...     agent_pbks,
    ...     good_pbks,
    ... )
    >>> game_initialization = GameInitialization(
    ...     money_amounts,
    ...     endowments,
    ...     utility_params
    ... )
    >>> game = Game(game_configuration, game_initialization)

    Get the scores:
    >>> game.get_scores()
    [20.0, 26.931471805599454, 40.79441541679836]
    """

    def __init__(self, configuration: GameConfiguration, initialization: GameInitialization):
        """
        Initialize a game.
        :param configuration: the game configuration.
        :param initialization: the game initialization.
        """
        self._configuration = configuration  # type GameConfiguration
        self._initialization = initialization  # type: GameInitialization
        self.transactions = []  # type: List[GameTransaction]

        self._initial_agent_states = dict(
            (agent_pbk,
                AgentState(
                    initialization.initial_money_amounts[i],
                    initialization.endowments[i],
                    initialization.utility_params[i]
                ))
            for agent_pbk, i in zip(configuration.agent_pbks, range(configuration.nb_agents)))  # type: Dict[str, AgentState]

        self.agent_states = dict(
            (agent_pbk,
                AgentState(
                    initialization.initial_money_amounts[i],
                    initialization.endowments[i],
                    initialization.utility_params[i]
                ))
            for agent_pbk, i in zip(configuration.agent_pbks, range(configuration.nb_agents)))  # type: Dict[str, AgentState]

        self.good_states = dict(
            (good_pbk,
                GoodState(
                    DEFAULT_PRICE
                ))
            for good_pbk in configuration.good_pbks)  # type: Dict[str, GoodState]

    @property
    def initialization(self) -> GameInitialization:
        return self._initialization

    @property
    def configuration(self) -> GameConfiguration:
        return self._configuration

    @property
    def initial_agent_states(self) -> Dict[str, 'AgentState']:
        return self._initial_agent_states

    @staticmethod
    def generate_game(nb_agents: int,
                      nb_goods: int,
                      money_endowment: int,
                      tx_fee: int,
                      lower_bound_factor: int,
                      upper_bound_factor: int,
                      agent_pbks: List[str],
                      good_pbks: List[str]) -> 'Game':
        """
        Generate a game, the endowments and the utilites.
        :param nb_agents: the number of agents.
        :param nb_goods: the number of goods.
        :param money_endowment: the initial amount of money for every agent.
        :param tx_fee: the fee to pay per transaction.
        :param lower_bound_factor: the lower bound of a uniform distribution.
        :param upper_bound_factor: the upper bound of a uniform distribution
        :param agent_pbks: the pbks for the agents.
        :param good_pbks: the pbks for the goods.
        :return: a game.
        """
        game_configuration = GameConfiguration(nb_agents, nb_goods, tx_fee, agent_pbks, good_pbks)

        initial_money_amounts = generate_initial_money_amounts(nb_agents, money_endowment)
        endowments = generate_endowments(nb_goods, nb_agents, lower_bound_factor, upper_bound_factor)
        utility_params = generate_utility_params(nb_agents, nb_goods)
        game_initialization = GameInitialization(initial_money_amounts, endowments, utility_params)

        return Game(game_configuration, game_initialization)

    def get_initial_scores(self) -> List[float]:
        """Get the initial scores for every agent."""
        return [agent_state.get_score() for agent_state in self.initial_agent_states.values()]

    def get_scores(self) -> List[float]:
        """Get the current scores for every agent."""
        return [agent_state.get_score() for agent_state in self.agent_states.values()]

    def get_agent_state_from_agent_pbk(self, agent_pbk: str) -> 'AgentState':
        """
        Get agent state from agent pbk.
        :param agent_pbk: the agent's pbk.
        :return: the agent state of the agent.
        """
        return self.agent_states[agent_pbk]

    def is_transaction_valid(self, tx: 'GameTransaction') -> bool:
        """
        Check whether the transaction is valid given the state of the game.
        :param tx: the game transaction.
        :return: True if the transaction is valid, False otherwise.
        :raises: AssertionError: if the data in the transaction are not allowed (e.g. negative amount).
        """

        # check if the buyer has enough balance to pay the transaction.
        if self.agent_states[tx.buyer_pbk].balance < tx.amount + self.configuration.tx_fee:
            return False

        # check if we have enough instances of goods, for every good involved in the transaction.
        seller_holdings = self.agent_states[tx.seller_pbk].current_holdings
        for good_id, bought_quantity in enumerate(tx.quantities_by_good_pbk.values()):
            if seller_holdings[good_id] < bought_quantity:
                return False

        return True

    def settle_transaction(self, tx: 'GameTransaction') -> None:
        """
        Settle a valid transaction.

        >>> nb_agents = 3
        >>> nb_goods = 3
        >>> tx_fee = 1.0
        >>> agent_pbks = ['tac_agent_0', 'tac_agent_1', 'tac_agent_2']
        >>> good_pbks = ['tac_good_0', 'tac_good_1', 'tac_good_2']
        >>> money_amounts = [20, 20, 20]
        >>> endowments = [
        ... [1, 1, 1],
        ... [2, 1, 1],
        ... [1, 1, 2]]
        >>> utility_params = [
        ... [20.0, 40.0, 40.0],
        ... [10.0, 50.0, 40.0],
        ... [40.0, 30.0, 30.0]]
        >>> game_configuration = GameConfiguration(
        ...     nb_agents,
        ...     nb_goods,
        ...     tx_fee,
        ...     agent_pbks,
        ...     good_pbks,
        ... )
        >>> game_initialization = GameInitialization(
        ...     money_amounts,
        ...     endowments,
        ...     utility_params
        ... )
        >>> game = Game(game_configuration, game_initialization)
        >>> agent_state_0 = game.agent_states['tac_agent_0'] # agent state of tac_agent_0
        >>> agent_state_1 = game.agent_states['tac_agent_1'] # agent state of tac_agent_1
        >>> agent_state_2 = game.agent_states['tac_agent_2'] # agent state of tac_agent_2
        >>> agent_state_0.balance, agent_state_0.current_holdings
        (20, [1, 1, 1])
        >>> agent_state_1.balance, agent_state_1.current_holdings
        (20, [2, 1, 1])
        >>> agent_state_2.balance, agent_state_2.current_holdings
        (20, [1, 1, 2])
        >>> game.settle_transaction(GameTransaction('tac_agent_0', 'tac_agent_1', 15, {0: 1, 1: 0, 2: 0}))
        >>> agent_state_0.balance, agent_state_0.current_holdings
        (4.0, [2, 1, 1])
        >>> agent_state_1.balance, agent_state_1.current_holdings
        (35, [1, 1, 1])

        :param tx: the game transaction.
        :return: None
        :raises: AssertionError if the transaction is not valid.
        """
        assert self.is_transaction_valid(tx)
        self.transactions.append(tx)
        buyer_state = self.agent_states[tx.buyer_pbk]
        seller_state = self.agent_states[tx.seller_pbk]

        nb_instances_traded = sum(tx.quantities_by_good_pbk.values())

        # update holdings and prices
        for good_id, good_pbk, quantity in enumerate(tx.quantities_by_good_pbk.items()):
            buyer_state._current_holdings[good_id] += quantity
            seller_state._current_holdings[good_id] -= quantity
            if quantity > 0:
                # for now the price is simply the amount proportional to the share in the bundle
                price = tx.amount / nb_instances_traded
                good_state = self.good_states[good_pbk]
                good_state.price = price

        # update balances and charge fee to buyer
        buyer_state.balance -= tx.amount + self.configuration.tx_fee
        seller_state.balance += tx.amount

    def get_holdings_matrix(self) -> List[Endowment]:
        """
        Get the holdings matrix of shape (nb_agents, nb_goods).
        :return: the holdings matrix.
        """
        result = list(map(lambda state: state.current_holdings, self.agent_states.values()))
        return result

    def get_balances(self) -> List[float]:
        """Get the current balances."""
        result = list(map(lambda state: state.balance, self.agent_states.values()))
        return result

    def get_prices(self) -> List[float]:
        """Get the current prices."""
        result = list(map(lambda state: state.price, self.good_states.values()))
        return result

    def get_holdings_summary(self) -> str:
        """
        Get holdings summary.

        >>> nb_agents = 3
        >>> nb_goods = 3
        >>> tx_fee = 1.0
        >>> agent_pbks = ['tac_agent_0', 'tac_agent_1', 'tac_agent_2']
        >>> good_pbks = ['tac_good_0', 'tac_good_1', 'tac_good_2']
        >>> money_amounts = [20, 20, 20]
        >>> endowments = [
        ... [1, 1, 1],
        ... [2, 1, 1],
        ... [1, 1, 2]]
        >>> utility_params = [
        ... [20.0, 40.0, 40.0],
        ... [10.0, 50.0, 40.0],
        ... [40.0, 30.0, 30.0]]
        >>> game_configuration = GameConfiguration(
        ...     nb_agents,
        ...     nb_goods,
        ...     tx_fee,
        ...     agent_pbks,
        ...     good_pbks,
        ... )
        >>> game_initialization = GameInitialization(
        ...     money_amounts,
        ...     endowments,
        ...     utility_params
        ... )
        >>> game = Game(game_configuration, game_initialization)
        >>> print(game.get_holdings_summary(), end="")
        tac_agent_0 [1, 1, 1]
        tac_agent_1 [2, 1, 1]
        tac_agent_2 [1, 1, 2]

        :return: a string representing the holdings for every agent.
        """
        result = ""
        for agent_pbk, agent_state in self.agent_states.items():
            result = result + agent_pbk + " " + str(agent_state._current_holdings) + "\n"
        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "configuration": self.configuration.to_dict(),
            "initialization": self.initialization.to_dict(),
            "transactions": [t.to_dict() for t in self.transactions]
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'Game':
        configuration = GameConfiguration.from_dict(d["configuration"])
        initialization = GameInitialization.from_dict(d["initialization"])

        game = Game(configuration, initialization)
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

    def __init__(self, money: int, endowment: Endowment, utility_params: UtilityParams):
        """
        Instantiate an agent state object.

        :param money: the money of the agent in this state.
        :param endowment: the endowment for every good.
        :param utility_params: the utility params for every good.
        :param tx_fee: the fee of a transaction (i.e. state transition)
        """
        assert len(endowment) == len(utility_params)
        self.balance = money
        # TODO: fix notation to utility_params
        self._utility_params = copy.copy(utility_params)
        self._current_holdings = copy.copy(endowment)

    @property
    def current_holdings(self):
        return copy.copy(self._current_holdings)

    @property
    def utility_params(self) -> UtilityParams:
        return copy.copy(self._utility_params)

    # TODO: potentially move the next three methods out as separate utilities; separate state (data) from member functions
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
        Simulate a transaction and get the resulting score (taking into account the fee)
        :param tx: a transaction object.
        :return: the score.
        """
        current_score = self.get_score()
        new_state = self.apply([tx], tx_fee)
        new_score = new_state.get_score()
        return new_score - current_score

    def check_transaction_is_consistent(self, tx: Transaction, tx_fee: float) -> bool:
        """
        Check if the transaction is consistent.  E.g. check that the agent state has enough money if it is a buyer
        or enough holdings if it is a seller.
        :return: True if the transaction is legal wrt the current state, false otherwise.
        """

        if tx.buyer:
            # check if we have the money.
            result = self.balance >= tx.amount + tx_fee
        else:
            # check if we have the goods.
            result = True
            for good_id, quantity in enumerate(tx.quantities_by_good_pbk.values()):
                result = result and (self._current_holdings[good_id] >= quantity)
        return result

    # TODO: think about potentially taking apply and update out (simplifies not having to worry about changing state from within the class)
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
        Update the agent state from a transaction request.
        :param tx: the transaction request message.
        :return: None
        """
        if tx.buyer:
            fees = tx.amount + tx_fee
            self.balance -= fees
        else:
            self.balance += tx.amount

        for good_id, quantity in enumerate(tx.quantities_by_good_pbk.values()):
            quantity_delta = quantity if tx.buyer else -quantity
            self._current_holdings[good_id] += quantity_delta

    def __copy__(self):
        return AgentState(self.balance, self.current_holdings, self.utility_params)

    def __str__(self):
        return "AgentState{}".format(pprint.pformat({
            "money": self.balance,
            "utility_params": self.utility_params,
            "current_holdings": self._current_holdings
        }))

    def __eq__(self, other) -> bool:
        return isinstance(other, AgentState) and \
            self.balance == other.balance and \
            self.utility_params == other.utility_params and \
            self._current_holdings == other._current_holdings


class GoodState:
    """Represent the state of a good during the game."""

    def __init__(self, price: float):
        """
        Instantiate an agent state object.

        :param price: price of the good in this state.
        """
        self.price = price

        self._check_consistency()

    def _check_consistency(self):
        """
        Check the consistency of the good state.
        :return: None
        :raises: AssertionError: if some constraint is not satisfied.
        """
        assert self.price >= 0, "The price must be non-negative."


class GameTransaction:
    """Represent a transaction between agents"""

    def __init__(self, buyer_pbk: str, seller_pbk: str, amount: int, quantities_by_good_pbk: Dict[str, int],
                 timestamp: Optional[datetime.datetime] = None):
        """
        Instantiate a game transaction object.

        :param buyer_pbk: the pbk of the buyer in the game.
        :param seller_pbk: the pbk of the seller in the game.
        :param amount: the amount transferred.
        :param quantities_by_good_pbk: a map from good pbk to the quantity transacted.
        :param timestamp: the timestamp of the transaction.
        """
        self.buyer_pbk = buyer_pbk
        self.seller_pbk = seller_pbk
        self.amount = amount
        self.quantities_by_good_pbk = quantities_by_good_pbk
        self.timestamp = datetime.datetime.now() if timestamp is None else timestamp

        self._check_consistency()

    def _check_consistency(self):
        """
        Check the consistency of the transaction parameters.
        :return: None
        :raises AssertionError if some constraint is not satisfied.
        """

        assert self.buyer_pbk != self.seller_pbk
        assert self.amount >= 0
        assert len(self.quantities_by_good_pbk.keys()) == len(set(self.quantities_by_good_pbk.keys()))
        assert all(quantity >= 0 for quantity in self.quantities_by_good_pbk.values())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "buyer_pbk": self.buyer_pbk,
            "seller_pbk": self.seller_pbk,
            "amount": self.amount,
            "quantities_by_good_pbk": self.quantities_by_good_pbk,
            "timestamp": str(self.timestamp)
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'GameTransaction':
        return cls(
            buyer_pbk=d["buyer_pbk"],
            seller_pbk=d["seller_pbk"],
            amount=d["amount"],
            quantities_by_good_pbk=quantities_by_good_pbk,
            timestamp=from_iso_format(d["timestamp"])
        )

    def __eq__(self, other) -> bool:
        return isinstance(other, GameTransaction) and \
            self.buyer_pbk == other.buyer_pbk and \
            self.seller_pbk == other.seller_pbk and \
            self.amount == other.amount and \
            self.quantities_by_good_pbk == other.quantities_by_good_pbk and \
            self.timestamp == other.timestamp

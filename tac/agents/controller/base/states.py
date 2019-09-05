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

"""This module contains classes to represent the TAC game.

Classes:

- GameInitialization: a class to hold the initialization of a game. Immutable.
- Game: the class that manages an instance of a game (e.g. validate and settling transactions).
"""

import logging
from typing import List, Dict, Any

from aea.mail.base import Address
from tac.agents.participant.v1.base.states import AgentState
from tac.platform.game.base import GameConfiguration, GoodState, Transaction
from tac.platform.game.helpers import generate_money_endowments, generate_good_endowments, generate_utility_params, \
    generate_equilibrium_prices_and_holdings, determine_scaling_factor


Endowment = List[int]  # an element e_j is the endowment of good j.
UtilityParams = List[float]  # an element u_j is the utility value of good j.

logger = logging.getLogger(__name__)

DEFAULT_PRICE = 0.0


class GameInitialization:
    """Class containing the game initialization of a TAC instance."""

    def __init__(self,
                 initial_money_amounts: List[float],
                 endowments: List[Endowment],
                 utility_params: List[UtilityParams],
                 eq_prices: List[float],
                 eq_good_holdings: List[List[float]],
                 eq_money_holdings: List[float]):
        """
        Instantiate a game initialization.

        :param initial_money_amounts: the initial amount of money of every agent.
        :param endowments: the endowments of the agents. A matrix where the first index is the agent id
                            and the second index is the good id. A generic element e_ij at row i and column j is
                            an integer that denotes the endowment of good j for agent i.
        :param utility_params: the utility params representing the preferences of the agents. A matrix where the first
                            index is the agent id and the second index is the good id. A generic element e_ij
                            at row i and column j is an integer that denotes the utility of good j for agent i.
        :param eq_prices: the competitive equilibrium prices of the goods. A list.
        :param eq_good_holdings: the competitive equilibrium good holdings of the agents. A matrix where the first index is the agent id
                            and the second index is the good id. A generic element g_ij at row i and column j is
                            a float that denotes the (divisible) amount of good j for agent i.
        :param eq_money_holdings: the competitive equilibrium money holdings of the agents. A list.
        """
        self._initial_money_amounts = initial_money_amounts
        self._endowments = endowments
        self._utility_params = utility_params
        self._eq_prices = eq_prices
        self._eq_good_holdings = eq_good_holdings
        self._eq_money_holdings = eq_money_holdings

        self._check_consistency()

    @property
    def initial_money_amounts(self) -> List[float]:
        """Get list of the initial amount of money of every agent."""
        return self._initial_money_amounts

    @property
    def endowments(self) -> List[Endowment]:
        """Get endowments of the agents."""
        return self._endowments

    @property
    def utility_params(self) -> List[UtilityParams]:
        """Get utility parameter list of the agents."""
        return self._utility_params

    @property
    def eq_prices(self) -> List[float]:
        """Get theoretical equilibrium prices (a benchmark)."""
        return self._eq_prices

    @property
    def eq_good_holdings(self) -> List[List[float]]:
        """Get theoretical equilibrium good holdings (a benchmark)."""
        return self._eq_good_holdings

    @property
    def eq_money_holdings(self) -> List[float]:
        """Get theoretical equilibrium money holdings (a benchmark)."""
        return self._eq_money_holdings

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

        assert len(self.eq_prices) == len(self.eq_good_holdings[0]), "Length of eq_prices and an element of eq_good_holdings must be the same."
        assert len(self.eq_good_holdings) == len(self.eq_money_holdings), "Length of eq_good_holdings and eq_good_holdings must be the same."

        assert all(len(row_e) == len(row_u) for row_e, row_u in zip(self.endowments, self.utility_params)), "Dimensions for utility_params and endowments rows must be the same."

    def to_dict(self) -> Dict[str, Any]:
        """Get a dictionary from the object."""
        return {
            "initial_money_amounts": self.initial_money_amounts,
            "endowments": self.endowments,
            "utility_params": self.utility_params,
            "eq_prices": self.eq_prices,
            "eq_good_holdings": self.eq_good_holdings,
            "eq_money_holdings": self.eq_money_holdings
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'GameInitialization':
        """Instantiate an object from the dictionary."""
        obj = cls(
            d["initial_money_amounts"],
            d["endowments"],
            d["utility_params"],
            d["eq_prices"],
            d["eq_good_holdings"],
            d["eq_money_holdings"]
        )
        return obj

    def __eq__(self, other):
        """Compare equality of two objects."""
        return isinstance(other, GameInitialization) and \
            self.initial_money_amounts == other.initial_money_amounts and \
            self.endowments == other.endowments and \
            self.utility_params == other.utility_params and \
            self.eq_prices == other.eq_prices and \
            self.eq_good_holdings == other.eq_good_holdings and \
            self.eq_money_holdings == other.eq_money_holdings


class Game:
    """
    Class representing a game instance of TAC.

    >>> nb_agents = 3
    >>> nb_goods = 3
    >>> tx_fee = 1.0
    >>> agent_pbk_to_name = {'tac_agent_0_pbk': 'tac_agent_0', 'tac_agent_1_pbk': 'tac_agent_1', 'tac_agent_2_pbk': 'tac_agent_2'}
    >>> good_pbk_to_name = {'tac_good_0': 'Good 0', 'tac_good_1': 'Good 1', 'tac_good_2': 'Good 2'}
    >>> money_amounts = [20, 20, 20]
    >>> endowments = [
    ... [1, 1, 1],
    ... [2, 1, 1],
    ... [1, 1, 2]]
    >>> utility_params = [
    ... [20.0, 40.0, 40.0],
    ... [10.0, 50.0, 40.0],
    ... [40.0, 30.0, 30.0]]
    >>> eq_prices = [1.0, 2.0, 2.0]
    >>> eq_good_holdings = [
    ... [1.0, 1.0, 1.0],
    ... [2.0, 1.0, 1.0],
    ... [1.0, 1.0, 2.0]]
    >>> eq_money_holdings = [20.0, 20.0, 20.0]
    >>> game_configuration = GameConfiguration(
    ...     nb_agents,
    ...     nb_goods,
    ...     tx_fee,
    ...     agent_pbk_to_name,
    ...     good_pbk_to_name
    ... )
    >>> game_initialization = GameInitialization(
    ...     money_amounts,
    ...     endowments,
    ...     utility_params,
    ...     eq_prices,
    ...     eq_good_holdings,
    ...     eq_money_holdings
    ... )
    >>> game = Game(game_configuration, game_initialization)

    Get the scores:
    >>> game.get_scores()
    {'tac_agent_0_pbk': 89.31471805599453, 'tac_agent_1_pbk': 93.36936913707618, 'tac_agent_2_pbk': 101.47867129923947}
    """

    def __init__(self, configuration: GameConfiguration, initialization: GameInitialization):
        """
        Initialize a game.

        :param configuration: the game configuration.
        :param initialization: the game initialization.
        """
        self._configuration = configuration  # type GameConfiguration
        self._initialization = initialization  # type: GameInitialization
        self.transactions = []  # type: List[Transaction]

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
        """Get game initialization."""
        return self._initialization

    @property
    def configuration(self) -> GameConfiguration:
        """Get game configuration."""
        return self._configuration

    @property
    def initial_agent_states(self) -> Dict[str, 'AgentState']:
        """Get initial state of each agent."""
        return self._initial_agent_states

    @staticmethod
    def generate_game(nb_agents: int,
                      nb_goods: int,
                      tx_fee: float,
                      money_endowment: int,
                      base_good_endowment: int,
                      lower_bound_factor: int,
                      upper_bound_factor: int,
                      agent_pbk_to_name: Dict[str, str],
                      good_pbk_to_name: Dict[str, str]) -> 'Game':
        """
        Generate a game, the endowments and the utilites.

        :param nb_agents: the number of agents.
        :param nb_goods: the number of goods.
        :param tx_fee: the fee to pay per transaction.
        :param money_endowment: the initial amount of money for every agent.
        :param base_good_endowment: the base amount of instances per good.
        :param lower_bound_factor: the lower bound of a uniform distribution.
        :param upper_bound_factor: the upper bound of a uniform distribution
        :param agent_pbk_to_name: the mapping of the public keys for the agents to their names.
        :param good_pbk_to_name: the mapping of the public keys for the goods to their names.
        :return: a game.
        """
        game_configuration = GameConfiguration(nb_agents, nb_goods, tx_fee, agent_pbk_to_name, good_pbk_to_name)

        scaling_factor = determine_scaling_factor(money_endowment)
        money_endowments = generate_money_endowments(nb_agents, money_endowment)
        good_endowments = generate_good_endowments(nb_goods, nb_agents, base_good_endowment, lower_bound_factor, upper_bound_factor)
        utility_params = generate_utility_params(nb_agents, nb_goods, scaling_factor)
        eq_prices, eq_good_holdings, eq_money_holdings = generate_equilibrium_prices_and_holdings(good_endowments, utility_params, money_endowment, scaling_factor)
        game_initialization = GameInitialization(money_endowments, good_endowments, utility_params, eq_prices, eq_good_holdings, eq_money_holdings)

        return Game(game_configuration, game_initialization)

    def get_initial_scores(self) -> List[float]:
        """Get the initial scores for every agent."""
        return [agent_state.get_score() for agent_state in self.initial_agent_states.values()]

    def get_scores(self) -> Dict[str, float]:
        """Get the current scores for every agent."""
        return {agent_pbk: agent_state.get_score() for agent_pbk, agent_state in self.agent_states.items()}

    def get_agent_state_from_agent_pbk(self, agent_pbk: Address) -> 'AgentState':
        """
        Get agent state from agent pbk.

        :param agent_pbk: the agent's pbk.
        :return: the agent state of the agent.
        """
        return self.agent_states[agent_pbk]

    def is_transaction_valid(self, tx: Transaction) -> bool:
        """
        Check whether the transaction is valid given the state of the game.

        :param tx: the transaction.
        :return: True if the transaction is valid, False otherwise.
        :raises: AssertionError: if the data in the transaction are not allowed (e.g. negative amount).
        """
        # check if the buyer has enough balance to pay the transaction.
        share_of_tx_fee = round(self.configuration.tx_fee / 2.0, 2)
        if self.agent_states[tx.buyer_pbk].balance < tx.amount + share_of_tx_fee:
            return False

        # check if we have enough instances of goods, for every good involved in the transaction.
        seller_holdings = self.agent_states[tx.seller_pbk].current_holdings
        for good_id, bought_quantity in enumerate(tx.quantities_by_good_pbk.values()):
            if seller_holdings[good_id] < bought_quantity:
                return False

        return True

    def settle_transaction(self, tx: Transaction) -> None:
        """
        Settle a valid transaction.

        >>> nb_agents = 3
        >>> nb_goods = 3
        >>> tx_fee = 1.0
        >>> agent_pbk_to_name = {'tac_agent_0_pbk': 'tac_agent_0', 'tac_agent_1_pbk': 'tac_agent_1', 'tac_agent_2_pbk': 'tac_agent_2'}
        >>> good_pbk_to_name = {'tac_good_0': 'Good 0', 'tac_good_1': 'Good 1', 'tac_good_2': 'Good 2'}
        >>> money_amounts = [20, 20, 20]
        >>> endowments = [
        ... [1, 1, 1],
        ... [2, 1, 1],
        ... [1, 1, 2]]
        >>> utility_params = [
        ... [20.0, 40.0, 40.0],
        ... [10.0, 50.0, 40.0],
        ... [40.0, 30.0, 30.0]]
        >>> eq_prices = [1.0, 2.0, 2.0]
        >>> eq_good_holdings = [
        ... [1.0, 1.0, 1.0],
        ... [2.0, 1.0, 1.0],
        ... [1.0, 1.0, 2.0]]
        >>> eq_money_holdings = [20.0, 20.0, 20.0]
        >>> game_configuration = GameConfiguration(
        ...     nb_agents,
        ...     nb_goods,
        ...     tx_fee,
        ...     agent_pbk_to_name,
        ...     good_pbk_to_name,
        ... )
        >>> game_initialization = GameInitialization(
        ...     money_amounts,
        ...     endowments,
        ...     utility_params,
        ...     eq_prices,
        ...     eq_good_holdings,
        ...     eq_money_holdings
        ... )
        >>> game = Game(game_configuration, game_initialization)
        >>> agent_state_0 = game.agent_states['tac_agent_0_pbk'] # agent state of tac_agent_0
        >>> agent_state_1 = game.agent_states['tac_agent_1_pbk'] # agent state of tac_agent_1
        >>> agent_state_2 = game.agent_states['tac_agent_2_pbk'] # agent state of tac_agent_2
        >>> agent_state_0.balance, agent_state_0.current_holdings
        (20, [1, 1, 1])
        >>> agent_state_1.balance, agent_state_1.current_holdings
        (20, [2, 1, 1])
        >>> agent_state_2.balance, agent_state_2.current_holdings
        (20, [1, 1, 2])
        >>> tx = Transaction('some_tx_id', True, 'tac_agent_1_pbk', 15, {'tac_good_0': 1, 'tac_good_1': 0, 'tac_good_2': 0}, 'tac_agent_0_pbk')
        >>> game.settle_transaction(tx)
        >>> agent_state_0.balance, agent_state_0.current_holdings
        (4.5, [2, 1, 1])
        >>> agent_state_1.balance, agent_state_1.current_holdings
        (34.5, [1, 1, 1])

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
        for good_id, (good_pbk, quantity) in enumerate(tx.quantities_by_good_pbk.items()):
            buyer_state._current_holdings[good_id] += quantity
            seller_state._current_holdings[good_id] -= quantity
            if quantity > 0:
                # for now the price is simply the amount proportional to the share in the bundle
                price = tx.amount / nb_instances_traded
                good_state = self.good_states[good_pbk]
                good_state.price = price

        share_of_tx_fee = round(self.configuration.tx_fee / 2.0, 2)
        # update balances and charge share of fee to buyer and seller
        buyer_state.balance -= tx.amount + share_of_tx_fee
        seller_state.balance += tx.amount - share_of_tx_fee

    def get_holdings_matrix(self) -> List[Endowment]:
        """
        Get the holdings matrix of shape (nb_agents, nb_goods).

        :return: the holdings matrix.
        """
        result = list(map(lambda state: state.current_holdings, self.agent_states.values()))
        return result

    def get_balances(self) -> Dict[str, float]:
        """Get the current balances."""
        result = {agent_pbk: agent_state.balance for agent_pbk, agent_state in self.agent_states.items()}
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
        >>> agent_pbk_to_name = {'tac_agent_0_pbk': 'tac_agent_0', 'tac_agent_1_pbk': 'tac_agent_1', 'tac_agent_2_pbk': 'tac_agent_2'}
        >>> good_pbk_to_name = {'tac_good_0': 'Good 0', 'tac_good_1': 'Good 1', 'tac_good_2': 'Good 2'}
        >>> money_amounts = [20, 20, 20]
        >>> endowments = [
        ... [1, 1, 1],
        ... [2, 1, 1],
        ... [1, 1, 2]]
        >>> utility_params = [
        ... [20.0, 40.0, 40.0],
        ... [10.0, 50.0, 40.0],
        ... [40.0, 30.0, 30.0]]
        >>> eq_prices = [1.0, 2.0, 2.0]
        >>> eq_good_holdings = [
        ... [1.0, 1.0, 1.0],
        ... [2.0, 1.0, 1.0],
        ... [1.0, 1.0, 2.0]]
        >>> eq_money_holdings = [20.0, 20.0, 20.0]
        >>> game_configuration = GameConfiguration(
        ...     nb_agents,
        ...     nb_goods,
        ...     tx_fee,
        ...     agent_pbk_to_name,
        ...     good_pbk_to_name
        ... )
        >>> game_initialization = GameInitialization(
        ...     money_amounts,
        ...     endowments,
        ...     utility_params,
        ...     eq_prices,
        ...     eq_good_holdings,
        ...     eq_money_holdings
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
            result = result + self.configuration.agent_pbk_to_name[agent_pbk] + " " + str(agent_state._current_holdings) + "\n"
        return result

    def get_equilibrium_summary(self) -> str:
        """Get equilibrium summary."""
        result = "Equilibrium prices: \n"
        for good_pbk, eq_price in zip(self.configuration.good_pbks, self.initialization.eq_prices):
            result = result + good_pbk + " " + str(eq_price) + "\n"
        result = result + "\n"
        result = result + "Equilibrium good allocation: \n"
        for agent_name, eq_allocation in zip(self.configuration.agent_names, self.initialization.eq_good_holdings):
            result = result + agent_name + " " + str(eq_allocation) + "\n"
        result = result + "\n"
        result = result + "Equilibrium money allocation: \n"
        for agent_name, eq_allocation in zip(self.configuration.agent_names, self.initialization.eq_money_holdings):
            result = result + agent_name + " " + str(eq_allocation) + "\n"
        return result

    def to_dict(self) -> Dict[str, Any]:
        """Get a dictionary from the object."""
        return {
            "configuration": self.configuration.to_dict(),
            "initialization": self.initialization.to_dict(),
            "transactions": [t.to_dict() for t in self.transactions]
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'Game':
        """Get class instance from dictionary."""
        configuration = GameConfiguration.from_dict(d["configuration"])
        initialization = GameInitialization.from_dict(d["initialization"])

        game = Game(configuration, initialization)
        for tx_dict in d["transactions"]:
            tx = Transaction.from_dict(tx_dict)
            game.settle_transaction(tx)

        return game

    def __eq__(self, other):
        """Compare equality of two instances from class."""
        return isinstance(other, Game) and \
            self.configuration == other.configuration and \
            self.transactions == other.transactions

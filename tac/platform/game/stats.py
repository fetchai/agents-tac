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

"""This module contains a class to query statistics about a game."""

from typing import Any, Dict, Optional, Tuple, List

import numpy as np

from tac.agents.controller.base.states import Game
from tac.agents.participant.v1.base.states import AgentState


class GameStats:
    """A class to query statistics about a game."""

    def __init__(self, game: Optional[Game]) -> None:
        """
        Instantiate game stats.

        :param game: the game

        :return: None
        """
        self.game = game  # type: Optional[Game]

    @classmethod
    def from_json(cls, d: Dict[str, Any]):
        """Read from json."""
        game = Game.from_dict(d)
        return GameStats(game)

    def holdings_history(self):
        """
        Compute the history of holdings.

        :return: a matrix of shape (nb_transactions, nb_agents, nb_goods). i=0 is the initial endowment matrix.
        """
        nb_transactions = len(self.game.transactions)
        nb_agents = self.game.configuration.nb_agents
        nb_goods = self.game.configuration.nb_goods
        result = np.zeros((nb_transactions + 1, nb_agents, nb_goods), dtype=np.int32)

        temp_game = Game(self.game.configuration, self.game.initialization)

        # initial holdings
        result[0, :] = np.asarray(temp_game.initialization.endowments, dtype=np.int32)

        # compute the partial scores for every agent after every transaction
        # (remember that indexes of the transaction start from one, because index 0 is reserved for the initial scores)
        for idx, tx in enumerate(self.game.transactions):
            temp_game.settle_transaction(tx)
            result[idx + 1, :] = np.asarray(temp_game.get_holdings_matrix(), dtype=np.int32)

        return result

    def score_history(self) -> Tuple[List[str], np.ndarray]:
        """
        Compute the history of the scores for every agent.

        To do so, we need to simulate the game again, by settling transactions one by one
        and get the scores after every transaction.

        :return: a matrix of shape (nb_transactions + 1, nb_agents), where every row i contains the scores
                 after transaction i (i=0 is a row with the initial scores.)
        """
        nb_transactions = len(self.game.transactions)
        nb_agents = self.game.configuration.nb_agents
        result = np.zeros((nb_transactions + 1, nb_agents))

        temp_game = Game(self.game.configuration, self.game.initialization)

        # initial scores
        scores_dict = temp_game.get_scores()
        result[0, :] = list(scores_dict.values())
        keys = list(scores_dict.keys())

        # compute the partial scores for every agent after every transaction
        # (remember that indexes of the transaction start from one, because index 0 is reserved for the initial scores)
        for idx, tx in enumerate(self.game.transactions):
            temp_game.settle_transaction(tx)
            scores_dict = temp_game.get_scores()
            result[idx + 1, :] = list(scores_dict.values())

        return keys, result

    def balance_history(self) -> Tuple[List[str], np.ndarray]:
        """Get the balance history."""
        nb_transactions = len(self.game.transactions)
        nb_agents = self.game.configuration.nb_agents
        result = np.zeros((nb_transactions + 1, nb_agents), dtype=np.int32)

        temp_game = Game(self.game.configuration, self.game.initialization)

        # initial balances
        balances_dict = temp_game.get_balances()
        result[0, :] = np.asarray(list(balances_dict.values()), dtype=np.int32)
        keys = list(balances_dict.keys())

        # compute the partial scores for every agent after every transaction
        # (remember that indexes of the transaction start from one, because index 0 is reserved for the initial scores)
        for idx, tx in enumerate(self.game.transactions):
            temp_game.settle_transaction(tx)
            balances_dict = temp_game.get_balances()
            result[idx + 1, :] = np.asarray(list(balances_dict.values()), dtype=np.int32)

        return keys, result

    def price_history(self) -> np.ndarray:
        """Get the price history."""
        nb_transactions = len(self.game.transactions)
        nb_goods = self.game.configuration.nb_goods
        result = np.zeros((nb_transactions + 1, nb_goods), dtype=np.float32)

        temp_game = Game(self.game.configuration, self.game.initialization)

        # initial prices
        result[0, :] = np.asarray(0, dtype=np.float32)

        for idx, tx in enumerate(self.game.transactions):
            temp_game.settle_transaction(tx)
            result[idx + 1, :] = np.asarray(temp_game.get_prices(), dtype=np.float32)

        return result

    def eq_vs_mean_price(self) -> Tuple[List[str], np.ndarray]:
        """
        Compute the mean price of each good and display it together with the equilibrium price.

        :return: a matrix of shape (2, nb_goods), where every column i contains the prices of the good.
        """
        nb_transactions = len(self.game.transactions)
        eq_prices = self.game.initialization.eq_prices
        nb_goods = len(eq_prices)

        result = np.zeros((2, nb_goods), dtype=np.float32)
        result[0, :] = np.asarray(eq_prices, dtype=np.float32)

        prices_by_transactions = np.zeros((nb_transactions + 1, nb_goods), dtype=np.float32)

        # initial prices
        prices_by_transactions[0, :] = np.asarray(0, dtype=np.float32)

        temp_game = Game(self.game.configuration, self.game.initialization)

        for idx, tx in enumerate(self.game.transactions):
            temp_game.settle_transaction(tx)
            prices_by_transactions[idx + 1, :] = np.asarray(temp_game.get_prices(), dtype=np.float32)

        denominator = (prices_by_transactions != 0).sum(0)
        result[1, :] = np.true_divide(prices_by_transactions.sum(0), denominator)
        result[1, denominator == 0] = 0

        result = np.transpose(result)

        return self.game.configuration.good_names, result

    def eq_vs_current_score(self) -> Tuple[List[str], np.ndarray]:
        """
        Compute the equilibrium score of each agent and display it together with the current score.

        :return: a matrix of shape (2, nb_agents), where every column i contains the scores of the agent.
        """
        nb_agents = self.game.configuration.nb_agents
        current_scores = np.zeros((1, nb_agents), dtype=np.float32)

        eq_agent_states = dict(
            (agent_pbk,
                AgentState(
                    self.game.initialization.eq_money_holdings[i],
                    self.game.initialization.eq_good_holdings[i],
                    self.game.initialization.utility_params[i]
                ))
            for agent_pbk, i in zip(self.game.configuration.agent_pbks, range(self.game.configuration.nb_agents)))  # type: Dict[str, AgentState]

        result = np.zeros((2, nb_agents), dtype=np.float32)
        result[0, :] = [eq_agent_state.get_score() for eq_agent_state in eq_agent_states.values()]

        temp_game = Game(self.game.configuration, self.game.initialization)

        # initial scores
        scores_dict = temp_game.get_scores()
        current_scores[0, :] = list(scores_dict.values())
        keys = list(scores_dict.keys())

        # compute the partial scores for every agent after every transaction
        # (remember that indexes of the transaction start from one, because index 0 is reserved for the initial scores)
        for idx, tx in enumerate(self.game.transactions):
            temp_game.settle_transaction(tx)
            scores_dict = temp_game.get_scores()
            current_scores[0, :] = list(scores_dict.values())

        result[1, :] = current_scores[0, :]
        result = np.transpose(result)

        return keys, result

    def adjusted_score(self) -> Tuple[List[str], np.ndarray]:
        """
        Compute the adjusted score of each agent.

        :return: a matrix of shape (1, nb_agents), where every column i contains the score of the agent.
        """
        nb_agents = self.game.configuration.nb_agents
        current_scores = np.zeros((1, nb_agents), dtype=np.float32)

        eq_agent_states = dict(
            (agent_pbk,
                AgentState(
                    self.game.initialization.eq_money_holdings[i],
                    self.game.initialization.eq_good_holdings[i],
                    self.game.initialization.utility_params[i]
                ))
            for agent_pbk, i in zip(self.game.configuration.agent_pbks, range(self.game.configuration.nb_agents)))  # type: Dict[str, AgentState]

        result = np.zeros((1, nb_agents), dtype=np.float32)

        eq_scores = np.zeros((1, nb_agents), dtype=np.float32)
        eq_scores[0, :] = [eq_agent_state.get_score() for eq_agent_state in eq_agent_states.values()]

        temp_game = Game(self.game.configuration, self.game.initialization)

        # initial scores
        initial_scores = np.zeros((1, nb_agents), dtype=np.float32)
        scores_dict = temp_game.get_scores()
        initial_scores[0, :] = list(scores_dict.values())
        keys = list(scores_dict.keys())
        current_scores = np.zeros((1, nb_agents), dtype=np.float32)
        current_scores[0, :] = initial_scores[0, :]

        # compute the partial scores for every agent after every transaction
        # (remember that indexes of the transaction start from one, because index 0 is reserved for the initial scores)
        for idx, tx in enumerate(self.game.transactions):
            temp_game.settle_transaction(tx)
            scores_dict = temp_game.get_scores()
            current_scores[0, :] = list(scores_dict.values())

        result[0, :] = np.divide(np.subtract(current_scores, initial_scores), np.subtract(eq_scores, initial_scores))
        result = np.transpose(result)

        return keys, result

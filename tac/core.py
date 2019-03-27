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
import pprint
import random
from typing import List

from oef.agents import OEFAgent


class TacAgent(OEFAgent):
    def __init__(self, public_key: str, oef_addr: str, oef_port: int = 3333, **kwargs) -> None:
        super().__init__(public_key, oef_addr, oef_port, **kwargs)


class Game(object):

    def __init__(self, nb_agents: int,
                 nb_goods: int,
                 initial_money_amount: int,
                 instances_per_good: int,
                 scores: List[int],
                 initial_endowments: List[List[int]],
                 preferences: List[List[int]]):
        """
        Initialize a game.

        :param nb_agents: the number of agents.
        :param nb_goods: the number of goods.
        :param initial_money_amount: the initial amount of money.
        :param scores: list of scores.
        :param instances_per_good: the number of instances per good.
        :param initial_endowments: the endowments of the agents. A matrix where the first index is the agent id and
                                   the second index is the good id. A generic element at row i and column j is
                                   an integer that denotes the amount of good j for agent i.
        :param preferences: the preferences of the agents. A matrix of integers where a generic row i
                            is a list of good ids, ordered accordingly to the agent's preference.
                            The index of good j in agent's row i represents the class of preference l for that good.
                            The associated score is scores[l].
        """
        self._check_consistency(nb_agents, nb_goods, initial_money_amount, instances_per_good, scores,
                                initial_endowments, preferences)
        self.nb_agents = nb_agents
        self.nb_goods = nb_goods
        self.instances_per_good = instances_per_good
        self.initial_money_amount = initial_money_amount
        self.scores = scores

        self.game_states = [GameState(initial_money_amount, initial_endowments[i], preferences[i], scores)
                            for i in range(nb_agents)]  # type: List[GameState]

    @classmethod
    def _check_consistency(cls, nb_agents: int,
                           nb_goods: int,
                           initial_money_amount: int,
                           instances_per_good: int,
                           scores: List[int],
                           initial_endowments: List[List[int]],
                           preferences: List[List[int]]):
        assert nb_agents > 0
        assert nb_goods > 0
        assert initial_money_amount > 0

        # TODO the number of instances can be slightly higher or lower than the number of agents. To be changed.
        assert instances_per_good >= nb_agents

        # we have a score for each class of preference (that is, "first preferred good", "second preferred good", etc.)
        # hence, the number of scores is equal to the number of goods.
        assert len(scores) == nb_goods
        # no negative scores.
        assert all(score >= 0 for score in scores)

        # Check the initial endowments.

        # we have an endowment for every agent.
        assert len(initial_endowments) == nb_agents
        # every endowment describes the amount for all the goods.
        assert all(len(row) == nb_goods for row in initial_endowments)
        # every element of the matrix must be a valid amount of good
        # (that is, between 0 and the number of instances per good)
        assert all(0 <= e_ij <= instances_per_good for row_i in initial_endowments for e_ij in row_i)
        # the sum of every column must be equal to the instances per good
        assert all(
            sum(initial_endowments[agent_id][good_id] for agent_id in range(nb_agents)) == instances_per_good for good_id in range(nb_goods))

        # Check the preferences.

        # we have a preference list for every agent
        assert len(preferences) == nb_agents
        # every preference is a list whose length is the number of goods.
        # every preference contains all the good ids
        assert all(len(preference) == len(set(preference)) == nb_goods for preference in preferences)
        assert all(min(preference) == 0 and max(preference) == nb_goods - 1 for preference in preferences)

    @staticmethod
    def generate_game(nb_agents: int, nb_goods: int, initial_money_amount: int,
                      instances_per_good: int, scores: List[int]) -> 'Game':
        """Generate a game, sampling the initial endowments and the preferences."""

        # compute random endowment
        initial_endowments = [[0] * nb_goods for _ in range(nb_agents)]
        for good_id in range(nb_goods):
            for _ in range(instances_per_good):
                agent_id = random.randint(0, nb_agents - 1)
                initial_endowments[agent_id][good_id] += 1

        # compute random preferences.
        # (permute every preference list randomly).
        preferences = [list(range(nb_goods))] * nb_agents
        preferences = list(map(lambda x: random.sample(x, len(x)), preferences))

        return Game(nb_agents, nb_goods, initial_money_amount, instances_per_good,
                    scores, initial_endowments, preferences)

    def get_game_data_by_agent_id(self, agent_id: int) -> 'GameState':
        return self.game_states[agent_id]


class GameState:
    """Represent the state of an agent during the game."""

    def __init__(self, money: int, initial_endowment: List[int], preferences: List[int], scores: List[int]):
        self.money = money
        self.initial_endowment = initial_endowment
        self.preferences = preferences
        self.scores = scores

        self._current_holdings = copy.deepcopy(self.initial_endowment)

    def add_good(self, good_id: int):
        self._current_holdings[good_id] += 1

    def remove_good(self, good_id: int):
        self._current_holdings[good_id] -= 1

    def get_score(self) -> int:
        holdings_score = sum(self.scores[i] * 1 if holding > 0 else 0 for i, holding in enumerate(self._current_holdings))
        money_score = self.money
        return holdings_score + money_score

    def __str__(self):
        return "GameState{}".format(pprint.pformat({
            "money": self.money,
            "initial_endowment": self.initial_endowment,
            "preferences": self.preferences,
            "scores": self.scores,
            "current_holdings": self._current_holdings
        }))

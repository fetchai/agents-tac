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
import json
import pprint
import random
from typing import List, Dict, Any

from oef.agents import OEFAgent
from oef.query import Query
from oef.schema import Description

from tac.helpers import PlantUMLGenerator, plantuml_gen


class TacAgent(OEFAgent):
    def __init__(self, public_key: str, oef_addr: str, oef_port: int = 3333, plantuml: bool=True, **kwargs) -> None:
        """
         :param plantuml: choose
        """
        super().__init__(public_key, oef_addr, oef_port, **kwargs)
        self.plantuml = plantuml
        self.plantuml_generator = plantuml_gen

    def add_drawable(self, d: PlantUMLGenerator.Drawable):
        if self.plantuml:
            self.plantuml_generator.add_drawable(d)

    def register_service(self, msg_id: int, service_description: Description) -> None:
        super().register_service(msg_id, service_description)
        self.add_drawable(PlantUMLGenerator.Transition(self.public_key, "OEF Node", "register_service(model={})"
                                                       .format(service_description.data_model.name)))

    def search_services(self, search_id: int, query: Query, additional_msg: str = "") -> None:
        super().search_services(search_id, query)
        self.add_drawable(PlantUMLGenerator.Transition(self.public_key, "OEF Node", "search_services(model={}{})"
                                                       .format(query.model.name,
                                                               ", " + additional_msg if additional_msg != "" else "")))

    def on_search_result(self, search_id: int, agents: List[str]):
        self.add_drawable(PlantUMLGenerator
                          .Transition("OEF Node", self.public_key, "search result: [{}]"
                                      .format(", ".join(sorted(map(lambda x: '"' + x + '"', agents))))))


class Game(object):

    def __init__(self, nb_agents: int,
                 nb_goods: int,
                 initial_money_amount: int,
                 instances_per_good: int,
                 scores: List[int],
                 fee: int,
                 initial_endowments: List[List[int]],
                 preferences: List[List[int]]):
        """
        Initialize a game.

        :param nb_agents: the number of agents.
        :param nb_goods: the number of goods.
        :param initial_money_amount: the initial amount of money.
        :param scores: list of scores.
        :param fee: the fee for a transaction.
        :param instances_per_good: the number of instances per good.
        :param initial_endowments: the endowments of the agents. A matrix where the first index is the agent id and
                                   the second index is the good id. A generic element at row i and column j is
                                   an integer that denotes the amount of good j for agent i.
        :param preferences: the preferences of the agents. A matrix of integers where a generic row i
                            is a list of good ids, ordered accordingly to the agent's preference.
                            The index of good j in agent's row i represents the class of preference l for that good.
                            The associated score is scores[l].
        """
        self._check_consistency(nb_agents, nb_goods, initial_money_amount, instances_per_good, scores, fee,
                                initial_endowments, preferences)
        self.nb_agents = nb_agents
        self.nb_goods = nb_goods
        self.instances_per_good = instances_per_good
        self.initial_money_amount = initial_money_amount
        self.scores = scores
        self.fee = fee

        self.transactions = []  # type: List[GameTransaction]
        self.game_states = [GameState(initial_money_amount, initial_endowments[i], preferences[i], scores)
                            for i in range(nb_agents)]  # type: List[GameState]

    @classmethod
    def _check_consistency(cls, nb_agents: int,
                           nb_goods: int,
                           initial_money_amount: int,
                           instances_per_good: int,
                           scores: List[int],
                           fee: int,
                           initial_endowments: List[List[int]],
                           preferences: List[List[int]]):
        assert nb_agents > 0
        assert nb_goods > 0
        assert initial_money_amount > 0
        assert fee > 0

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
                      instances_per_good: int, scores: List[int], fee: int) -> 'Game':
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
                    scores, fee, initial_endowments, preferences)

    def get_game_data_by_agent_id(self, agent_id: int) -> 'GameState':
        return self.game_states[agent_id]

    def is_transaction_valid(self, tx: 'GameTransaction') -> bool:
        assert tx.buyer_id != tx.seller_id
        assert 0 <= tx.buyer_id < self.nb_agents
        assert 0 <= tx.seller_id < self.nb_agents
        assert all(q >= 0 for q in tx.quantities)
        assert tx.amount >= 0

        result = True
        result = result and self.game_states[tx.buyer_id].balance >= tx.amount + self.fee
        result = result and all(self.game_states[tx.seller_id].current_holdings[tx.good_ids[i]] >= tx.quantities[i]
                                for i in range(len(tx.good_ids)))

        return result

    def settle_transaction(self, tx: 'GameTransaction'):
        self.transactions.append(tx)
        buyer_state = self.game_states[tx.buyer_id]
        seller_state = self.game_states[tx.seller_id]

        # update holdings
        for good_id, quantity in zip(tx.good_ids, tx.quantities):
            buyer_state.current_holdings[good_id] += quantity
            seller_state.current_holdings[good_id] -= quantity

        # update balances
        buyer_state.balance -= tx.amount
        seller_state.balance += tx.amount

    def get_holdings_summary(self) -> str:
        result = ""
        for i, game_state in enumerate(self.game_states):
            result = result + "{:02d}".format(i) + " " + str(game_state.current_holdings) + "\n"
        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nb_agents": self.nb_agents,
            "nb_goods": self.nb_goods,
            "instances_per_good": self.instances_per_good,
            "scores": self.scores,
            "fee": self.fee,
            "transactions": [t.to_dict() for t in self.transactions]
        }


class GameState:
    """Represent the state of an agent during the game."""

    def __init__(self, money: int, initial_endowment: List[int], preferences: List[int], scores: List[int]):
        self.balance = money
        assert len(initial_endowment) == len(preferences) == len(scores)
        self.initial_endowment = initial_endowment
        self.preferences = preferences
        self.scores = scores

        self.current_holdings = copy.copy(self.initial_endowment)
        self._from_good_to_preference = dict(map(reversed, enumerate(self.preferences)))

    @property
    def nb_goods(self):
        return len(self.scores)

    def get_score(self) -> int:
        holdings_score = sum(self.scores[self._from_good_to_preference[i]] * (1 if holding > 0 else 0)
                             for i, holding in enumerate(self.current_holdings))
        money_score = self.balance
        return holdings_score + money_score

    def get_price_from_quantities_vector(self, quantities: List[int]):
        """
        Return the price of a vector of good quantities.
        :param quantities: the vector of good quantities
        :return: the overall price.
        """
        return sum(q * self.scores[idx] for idx, q in enumerate(quantities))

    def get_excess_goods_quantities(self):
        """
        Return the vector of good quantities in excess. A quantity for a good is in excess if it is more than 1.
        E.g. if an agent holds the good quantities [0, 2, 1], this function returns [0, 1, 0].
        :return: the vector of good quantities in excess.
        """
        return [q - 1 if q > 1 else 0 for q in self.current_holdings]

    def update(self, buyer: bool, amount: int, good_ids: List[int], quantities: List[int]):
        switch = 1 if buyer else -1
        for good_id, quantity in zip(good_ids, quantities):
            self.current_holdings[good_id] += switch * quantity
            self.balance -= switch * amount

    def __str__(self):
        return "GameState{}".format(pprint.pformat({
            "money": self.balance,
            "initial_endowment": self.initial_endowment,
            "preferences": self.preferences,
            "scores": self.scores,
            "current_holdings": self.current_holdings
        }))


class GameTransaction:
    """Represent a transaction between agents"""

    def __init__(self, buyer_id: int, seller_id: int, amount: int, good_ids: List[int], quantities: List[int]):
        assert len(good_ids) == len(quantities)
        self.buyer_id = buyer_id
        self.seller_id = seller_id
        self.amount = amount
        self.good_ids = good_ids
        self.quantities = quantities

    def to_dict(self) -> Dict[str, Any]:
        return {
            "buyer_id": self.buyer_id,
            "seller_id": self.seller_id,
            "amount": self.amount,
            "good_ids": self.good_ids,
            "quantities": self.quantities
        }

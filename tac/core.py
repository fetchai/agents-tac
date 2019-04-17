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
import asyncio
import copy
import datetime
import logging
import pprint
import random
import threading
from abc import abstractmethod
from typing import List, Dict, Any, Optional, Callable

import numpy as np
from oef.agents import OEFAgent
from oef.dialogue import DialogueAgent
from oef.messages import OEFErrorOperation, CFP_TYPES
from oef.proxy import OEFNetworkProxy
from oef.query import Query
from oef.schema import Description

from tac.helpers.misc import sample_good_instance, compute_endowment_of_good, TacError
from tac.helpers.plantuml import plantuml_gen
from tac.protocol import Register, Response, GameData, TransactionConfirmation, Error

logger = logging.getLogger(__name__)


class TacAgent(OEFAgent):
    def __init__(self, public_key: str, oef_addr: str, oef_port: int = 3333, **kwargs) -> None:
        super().__init__(public_key, oef_addr, oef_port, **kwargs)

    def register_service(self, msg_id: int, service_description: Description) -> None:
        super().register_service(msg_id, service_description)
        plantuml_gen.register_service(self.public_key, service_description)

    def search_services(self, search_id: int, query: Query, additional_msg: str = "") -> None:
        super().search_services(search_id, query)
        plantuml_gen.search_services(self.public_key, query, additional_msg=additional_msg)

    def on_search_result(self, search_id: int, agents: List[str]):
        plantuml_gen.on_search_result(self.public_key, agents)


class NegotiationAgent(DialogueAgent):

    def __init__(self, public_key: str, oef_addr: str, oef_port: int = 3333, **kwargs) -> None:
        super().__init__(OEFNetworkProxy(public_key, oef_addr, oef_port, **kwargs))
        self.controller = None  # type: Optional[str]
        self.game_state = None  # type: Optional[GameState]

        self.pending_search_ids = set()
        self.search_events = {} # type: Dict[int, asyncio.Event]
        self.search_results = {}  # type: Dict[int, List[str]]
        self.search_callbacks = {}  # type: Dict[int, Callable]

    def on_search_result(self, search_id: int, agents: List[str]):
        if search_id in self.pending_search_ids:
            # check if the search operation has a callback or it does not.
            if search_id in self.search_events:
                self.search_results[search_id] = agents
                self.search_events[search_id].set()
            elif search_id in self.search_callbacks:
                callback = self.search_callbacks[search_id]
                callback(self, agents)

    async def search(self, query: Query, callback: Optional[Callable[['TacAgent', Any], Any]] = None) -> Optional[List[str]]:
        """
        Search for agents. It uses the SDK's search_services() method.
        The main purpose of this method is to implement a blocking call such that waits until the OEF answers with a list of agents.
        Or, specify a custom function callback that will be executed when the result arrives.

        :param query: the query for the search.
        :param callback: if None, the search operation is synchronous (that is, waits until the OEF answers with the result).
                         The callbacks accepts 'self' as first argument and a list of strings as second argument.
        :return: a list of agent's public keys. If a callback is provided, return None.
        """
        search_id = len(self.pending_search_ids)
        self.pending_search_ids.add(search_id)
        self.search_services(search_id, query)
        if callback is not None:
            # register a callback
            self.search_callbacks[search_id] = callback
            return None
        else:
            event = threading.Event()
            self.search_events[search_id] = event
            event.wait()
            result = self.search_results[search_id]
            self.pending_search_ids.remove(search_id)
            self.search_events.pop(search_id)
            self.search_results.pop(search_id)
            return result

    @abstractmethod
    def on_start(self, game_data: GameData) -> None:
        """
        On receiving game data from the TAC controller, do the setup.

        :param game_data: the set of parameters assigned to this agent by the TAC controller.
        :return: ``None``
        """

    @abstractmethod
    def on_transaction_confirmed(self, tx_confirmation: TransactionConfirmation) -> None:
        """
        Handle the transaction confirmation.

        :param tx_confirmation: the data of the confirmed transaction.
        :return: ``None``
        """

    @abstractmethod
    def on_tac_error(self, error: Error) -> None:
        """
        Handle error messages from the TAC controller.

        :return: ``None``
        """

    @abstractmethod
    def on_new_cfp(self, msg_id: int, dialogue_id: int, from_: str, target: int, query: CFP_TYPES) -> None:
        """
        Handle the arrival of a CFP message.

        :param msg_id: the message identifier for the dialogue.
        :param dialogue_id: the identifier of the dialogue in which the message is sent.
        :param from_: the identifier of the agent who sent the message.
        :param target: the identifier of the message to whom this message is answering.
        :param query: the query associated with the Call For Proposals.
        :return: ``None``
        """

    def on_new_message(self, msg_id: int, dialogue_id: int, from_: str, content: bytes) -> None:
        """TODO Temporarily assume we can receive simple messages only from the controller agent."""
        # here we can get a new message either from any agent, including the controller.
        # however, the one from the controller should be handled in a different way.
        # try to parse it as if it were a response from the Controller.

        response = None  # type: Optional[Response]
        try:
            response = Response.from_pb(content)
        except TacError as e:
            # the message was not a 'Response' message.
            logger.exception(str(e))

        if isinstance(response, GameData):
            self.on_start(response)
        elif isinstance(response, TransactionConfirmation):
            self.on_transaction_confirmed(response)
        elif isinstance(response, Error):
            self.on_tac_error(response)
        else:
            # TODO revise.
            raise TacError("No correct message received.")

    def register(self, tac_controller_pk: str) -> None:
        """Register to a competition.
        :param tac_controller_pk: the public key of the controller.
        :return: ``None``
        :raises AssertionError: if the agent is already registered.
        """
        assert self.controller is None and self.game_state is None
        msg = Register(self.public_key).serialize()
        self.send_message(0, 0, tac_controller_pk, msg)

    def search_tac_controllers(self):
        pass


class Game(object):

    def __init__(self, nb_agents: int,
                 nb_goods: int,
                 initial_money_amount: int,
                 instances_per_good: List[int],
                 scores: List[int],
                 fee: int,
                 initial_endowments: List[List[int]],
                 preferences: List[List[int]],
                 agents_ids: List[str]):
        """
        Initialize a game.

        :param nb_agents: the number of agents.
        :param nb_goods: the number of goods.
        :param initial_money_amount: the initial amount of money.
        :param scores: list of scores.
        :param fee: the fee for a transaction.
        :param instances_per_good: a list with the number of instances per every good.
        :param initial_endowments: the endowments of the agents. A matrix where the first index is the agent id and
                                   the second index is the good id. A generic element at row i and column j is
                                   an integer that denotes the amount of good j for agent i.
        :param preferences: the preferences of the agents. A matrix of integers where a generic row i
                            is a list of good ids, ordered accordingly to the agent's preference.
                            The index of good j in agent's row i represents the class of preference l for that good.
                            The associated score is scores[l].
        :param agents_ids: a list of agents ids (as strings).
        """
        self._check_consistency(nb_agents, nb_goods, initial_money_amount, instances_per_good, scores, fee,
                                initial_endowments, preferences, agents_ids)
        self.nb_agents = nb_agents
        self.nb_goods = nb_goods
        self.instances_per_good = instances_per_good
        self.initial_money_amount = initial_money_amount
        self.initial_endowments = initial_endowments
        self.preferences = preferences
        self.scores = scores
        self.fee = fee
        self.agents_ids = agents_ids

        self._from_agent_pbk_to_agent_id = dict(map(reversed, enumerate(self.agents_ids)))

        self.transactions = []  # type: List[GameTransaction]
        self.game_states = [GameState(agents_ids[i], initial_money_amount, initial_endowments[i], preferences[i], scores)
                            for i in range(nb_agents)]  # type: List[GameState]

    @classmethod
    def _check_consistency(cls, nb_agents: int,
                           nb_goods: int,
                           initial_money_amount: int,
                           instances_per_good: List[int],
                           scores: List[int],
                           fee: int,
                           initial_endowments: List[List[int]],
                           preferences: List[List[int]],
                           agents_ids: List[str]):
        assert nb_agents > 0
        assert nb_goods > 0
        assert initial_money_amount > 0
        assert fee > 0

        assert len(agents_ids) >= nb_agents

        # # TODO the number of instances can be slightly higher or lower than the number of agents. To be changed.
        # assert instances_per_good >= nb_agents

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
        assert all(0 <= e_ij <= instances_per_good[good_id] for row_i in initial_endowments for good_id, e_ij in enumerate(row_i))
        # the sum of every column must be equal to the instances per good
        assert all(
            sum(initial_endowments[agent_id][good_id] for agent_id in range(nb_agents)) == instances_per_good[good_id]
            for good_id in range(nb_goods)
        )

        # Check the preferences.

        # we have a preference list for every agent
        assert len(preferences) == nb_agents
        # every preference is a list whose length is the number of goods.
        # every preference contains all the good ids
        assert all(len(preference) == len(set(preference)) == nb_goods for preference in preferences)
        assert all(min(preference) == 0 and max(preference) == nb_goods - 1 for preference in preferences)

    @staticmethod
    def generate_game(nb_agents: int, nb_goods: int, initial_money_amount: int,
                      scores: List[int], fee: int, agent_ids: List[str], g: int = 3) -> 'Game':
        """Generate a game, sampling the initial endowments and the preferences."""

        instances_per_good = [sample_good_instance(nb_agents, g) for _ in range(nb_goods)]
        endowments_by_good = [compute_endowment_of_good(nb_agents, I_j) for I_j in instances_per_good]
        initial_endowments = np.asarray(endowments_by_good).T.tolist()

        # compute random preferences.
        # (permute every preference list randomly).
        preferences = [list(range(nb_goods))] * nb_agents
        preferences = list(map(lambda x: random.sample(x, len(x)), preferences))

        return Game(nb_agents, nb_goods, initial_money_amount, instances_per_good,
                    scores, fee, initial_endowments, preferences, agent_ids)

    def get_scores(self) -> List[int]:
        """Get the current scores for every agent."""
        return [gs.get_score() for gs in self.game_states]

    def get_game_data_from_agent_id(self, agent_id: int) -> 'GameState':
        return self.game_states[agent_id]

    def get_game_data_from_agent_pbk(self, agent_pbk: str) -> 'GameState':
        """
        Get game data from agent public key.
        :param agent_pbk: the agent's public key.
        :return: the game state of the agent
        """
        return self.get_game_data_from_agent_id(self._from_agent_pbk_to_agent_id[agent_pbk])

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
            "initial_money_amount": self.initial_money_amount,
            "instances_per_good": self.instances_per_good,
            "scores": self.scores,
            "fee": self.fee,
            "initial_endowments": self.initial_endowments,
            "preferences": self.preferences,
            "agents_ids": self.agents_ids,
            "transactions": [t.to_dict() for t in self.transactions]
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'Game':
        obj = cls(
            d["nb_agents"],
            d["nb_goods"],
            d["initial_money_amount"],
            d["instances_per_good"],
            d["scores"],
            d["fee"],
            d["initial_endowments"],
            d["preferences"],
            d["agents_ids"]
        )

        for tx_dict in d["transactions"]:
            tx = GameTransaction.from_dict(tx_dict)
            obj.settle_transaction(tx)

        return obj


class GameState:
    """Represent the state of an agent during the game."""

    def __init__(self, agent_id: str, money: int, initial_endowment: List[int], preferences: List[int], scores: List[int]):
        self.agent_id = agent_id
        self.initial_money = money
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

    @property
    def scores_by_good(self):
        return [self._from_good_to_preference[good_id] for good_id in range(self.nb_goods)]

    def get_score(self) -> int:
        holdings_score = self.score_good_quantities(self.current_holdings)
        money_score = self.balance
        return holdings_score + money_score

    def score_good_quantity(self, good_id: int, quantity: int) -> int:
        assert 0 <= good_id < self.nb_goods
        assert 0 <= quantity
        return self.scores[self._from_good_to_preference[good_id]] * (1 if quantity >= 1 else 0)

    def score_good_quantities(self, quantities: List[int]) -> int:
        assert len(quantities) == self.nb_goods
        return sum(self.score_good_quantity(good_id, q) for good_id, q in enumerate(quantities))

    def get_price_from_quantities_vector(self, quantities: List[int]):
        """
        Return the price of a vector of good quantities.
        :param quantities: the vector of good quantities
        :return: the overall price.
        """
        assert len(quantities) == self.nb_goods
        return sum(q * self.scores[idx] for idx, q in enumerate(quantities))

    def get_excess_goods_quantities(self):
        """
        Return the vector of good quantities in excess. A quantity for a good is in excess if it is more than 1.
        E.g. if an agent holds the good quantities [0, 2, 1], this function returns [0, 1, 0].
        :return: the vector of good quantities in excess.
        """
        return [q - 1 if q > 1 else 0 for q in self.current_holdings]

    def get_score_after_transaction(self, d_money: int, d_holdings: List[int]) -> int:
        """
        Simulate a transaction and get the resulting score.
        :param d_money: the delta amount of money.
                        A negative value means that we pay money in the transaction.
                        A positive value means that we gain money from the transaction.
        :param d_holdings: a list of integers containing the delta quantities for every good.
                           A negative value ``q`` at position ``i`` means that we sold ``q`` instances of good ``i``.
                           A positive value ``q`` at position ``i`` means that we bought ``q`` instances of good ``i``.
        :return: the score that we would get if the transaction is confirmed.
        """
        new_holdings = np.asarray(self.current_holdings) + np.asarray(d_holdings)
        new_holdings_score = self.score_good_quantities(new_holdings)
        new_money = self.balance + d_money
        return new_holdings_score + new_money

    def update(self, buyer: bool, amount: int, good_ids: List[int], quantities: List[int]) -> None:
        """
        Update the game state.

        :param buyer: whether the values of the transaction have to be intended as a seller or as a buyer.
        :param amount: the amount of money involved in the transaction.
        :param good_ids: the good ids involved in the transaction.
        :param quantities: the quantities associated to the good ids involved in the transaction.
        :return: None
        """
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

    def __init__(self, buyer_id: int, seller_id: int, amount: int, good_ids: List[int], quantities: List[int],
                 timestamp: Optional[datetime.datetime] = None):
        assert len(good_ids) == len(quantities)
        self.buyer_id = buyer_id
        self.seller_id = seller_id
        self.amount = amount
        self.good_ids = good_ids
        self.quantities = quantities
        self.timestamp = datetime.datetime.now() if timestamp is None else timestamp

    def to_dict(self) -> Dict[str, Any]:
        return {
            "buyer_id": self.buyer_id,
            "seller_id": self.seller_id,
            "amount": self.amount,
            "good_ids": self.good_ids,
            "quantities": self.quantities,
            "timestamp": str(self.timestamp)
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'GameTransaction':
        return cls(
            buyer_id=d["buyer_id"],
            seller_id=d["seller_id"],
            amount=d["amount"],
            good_ids=d["good_ids"],
            quantities=d["quantities"],
            timestamp=d["timestamp"]
        )

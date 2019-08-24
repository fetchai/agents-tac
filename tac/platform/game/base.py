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
- WorldState represent the state of the world from the perspective of the agent.
"""
import copy
from enum import Enum
import logging
from typing import List, Dict, Any

from aea.mail.base import Address
from aea.protocols.tac.message import TACMessage
from aea.protocols.oef.models import Description

Endowment = List[int]  # an element e_j is the endowment of good j.
UtilityParams = List[float]  # an element u_j is the utility value of good j.
TransactionId = str

logger = logging.getLogger(__name__)

DEFAULT_PRICE = 0.0


class GamePhase(Enum):
    """This class defines the TAC game stages."""

    PRE_GAME = 'pre_game'
    GAME_SETUP = 'game_setup'
    GAME = 'game'
    POST_GAME = 'post_game'


class GameConfiguration:
    """Class containing the game configuration of a TAC instance."""

    def __init__(self,
                 nb_agents: int,
                 nb_goods: int,
                 tx_fee: float,
                 agent_pbk_to_name: Dict[str, str],
                 good_pbk_to_name: Dict[str, str]):
        """
        Instantiate a game configuration.

        :param nb_agents: the number of agents.
        :param nb_goods: the number of goods.
        :param tx_fee: the fee for a transaction.
        :param agent_pbk_to_name: a dictionary mapping agent public keys to agent names (as strings).
        :param good_pbk_to_name: a dictionary mapping good public keys to good names (as strings).
        """
        self._nb_agents = nb_agents
        self._nb_goods = nb_goods
        self._tx_fee = tx_fee
        self._agent_pbk_to_name = agent_pbk_to_name
        self._good_pbk_to_name = good_pbk_to_name

        self._check_consistency()

    @property
    def nb_agents(self) -> int:
        """Agent number of a TAC instance."""
        return self._nb_agents

    @property
    def nb_goods(self) -> int:
        """Good number of a TAC instance."""
        return self._nb_goods

    @property
    def tx_fee(self) -> float:
        """Transaction fee for the TAC instance."""
        return self._tx_fee

    @property
    def agent_pbk_to_name(self) -> Dict[str, str]:
        """Map agent public keys to names."""
        return self._agent_pbk_to_name

    @property
    def good_pbk_to_name(self) -> Dict[str, str]:
        """Map good public keys to names."""
        return self._good_pbk_to_name

    @property
    def agent_pbks(self) -> List[str]:
        """List of agent public keys."""
        return list(self._agent_pbk_to_name.keys())

    @property
    def agent_names(self):
        """List of agent names."""
        return list(self._agent_pbk_to_name.values())

    @property
    def good_pbks(self) -> List[str]:
        """List of good public keys."""
        return list(self._good_pbk_to_name.keys())

    @property
    def good_names(self) -> List[str]:
        """List of good names."""
        return list(self._good_pbk_to_name.values())

    def _check_consistency(self):
        """
        Check the consistency of the game configuration.

        :return: None
        :raises: AssertionError: if some constraint is not satisfied.
        """
        assert self.tx_fee >= 0, "Tx fee must be non-negative."
        assert self.nb_agents > 1, "Must have at least two agents."
        assert self.nb_goods > 1, "Must have at least two goods."
        assert len(self.agent_pbks) == self.nb_agents, "There must be one public key for each agent."
        assert len(set(self.agent_names)) == self.nb_agents, "Agents' names must be unique."
        assert len(self.good_pbks) == self.nb_goods, "There must be one public key for each good."
        assert len(set(self.good_names)) == self.nb_goods, "Goods' names must be unique."

    def to_dict(self) -> Dict[str, Any]:
        """Get a dictionary from the object."""
        return {
            "nb_agents": self.nb_agents,
            "nb_goods": self.nb_goods,
            "tx_fee": self.tx_fee,
            "agent_pbk_to_name": self.agent_pbk_to_name,
            "good_pbk_to_name": self.good_pbk_to_name
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'GameConfiguration':
        """Instantiate an object from the dictionary."""
        obj = cls(
            d["nb_agents"],
            d["nb_goods"],
            d["tx_fee"],
            d["agent_pbk_to_name"],
            d["good_pbk_to_name"]
        )
        return obj

    def __eq__(self, other):
        """Compare equality of two objects."""
        return isinstance(other, GameConfiguration) and \
            self.nb_agents == other.nb_agents and \
            self.nb_goods == other.nb_goods and \
            self.tx_fee == other.tx_fee and \
            self.agent_pbk_to_name == other.agent_pbk_to_name and \
            self.good_pbk_to_name == other.good_pbk_to_name


class GoodState:
    """Represent the state of a good during the game."""

    def __init__(self, price: float) -> None:
        """
        Instantiate an agent state object.

        :param price: price of the good in this state.
        :return: None
        """
        self.price = price

        self._check_consistency()

    def _check_consistency(self) -> None:
        """
        Check the consistency of the good state.

        :return: None
        :raises: AssertionError: if some constraint is not satisfied.
        """
        assert self.price >= 0, "The price must be non-negative."


class Transaction:
    """Convenience representation of a transaction."""

    def __init__(self, transaction_id: TransactionId, is_sender_buyer: bool, counterparty: Address,
                 amount: float, quantities_by_good_pbk: Dict[str, int], sender: Address) -> None:
        """
        Instantiate transaction request.

        :param transaction_id: the id of the transaction.
        :param is_sender_buyer: whether the transaction is sent by a buyer.
        :param counterparty: the counterparty of the transaction.
        :param amount: the amount of money involved.
        :param quantities_by_good_pbk: a map from good pbk to the quantity of that good involved in the transaction.
        :param sender: the sender of the transaction.

        :return: None
        """
        self.transaction_id = transaction_id
        self.is_sender_buyer = is_sender_buyer
        self.counterparty = counterparty
        self.amount = amount
        self.quantities_by_good_pbk = quantities_by_good_pbk
        self.sender = sender

        self._check_consistency()

    @property
    def sender(self):
        """Get the sender public key."""
        return self.sender

    @property
    def buyer_pbk(self) -> str:
        """Get the publick key of the buyer."""
        result = self.sender if self.is_sender_buyer else self.counterparty
        return result

    @property
    def seller_pbk(self) -> str:
        """Get the publick key of the seller."""
        result = self.counterparty if self.is_sender_buyer else self.sender
        return result

    def _check_consistency(self) -> None:
        """
        Check the consistency of the transaction parameters.

        :return: None
        :raises AssertionError if some constraint is not satisfied.
        """
        assert self.sender != self.counterparty
        assert self.amount >= 0
        assert len(self.quantities_by_good_pbk.keys()) == len(set(self.quantities_by_good_pbk.keys()))
        assert all(quantity >= 0 for quantity in self.quantities_by_good_pbk.values())

    def to_dict(self) -> Dict[str, Any]:
        """From object to dictionary."""
        return {
            "transaction_id": self.transaction_id,
            "is_sender_buyer": self.is_sender_buyer,
            "counterparty": self.counterparty,
            "amount": self.amount,
            "quantities_by_good_pbk": self.quantities_by_good_pbk,
            "sender": self.sender
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'Transaction':
        """Return a class instance from a dictionary."""
        return cls(
            transaction_id=d["transaction_id"],
            is_sender_buyer=d["is_sender_buyer"],
            counterparty=d["counterparty"],
            amount=d["amount"],
            quantities_by_good_pbk=d["quantities_by_good_pbk"],
            sender=d["sender"]
        )

    @classmethod
    def from_proposal(cls, proposal: Description, transaction_id: TransactionId,
                      is_sender_buyer: bool, counterparty: Address, sender: Address) -> 'Transaction':
        """
        Create a transaction from a proposal.

        :param proposal: the proposal
        :param transaction_id: the transaction id
        :param is_sender_buyer: whether the sender is the buyer
        :param counterparty: the counterparty public key
        :param sender: the sender public key
        :return: Transaction
        """
        data = copy.deepcopy(proposal.values)
        price = data.pop("price")
        quantity_by_good_pbk = {key: value for key, value in data.items()}
        return Transaction(transaction_id, is_sender_buyer, counterparty, price, quantity_by_good_pbk, sender)

    @classmethod
    def from_message(cls, message: TACMessage, sender: Address) -> 'Transaction':
        """
        Create a transaction from a proposal.

        :param message: the message
        :return: Transaction
        """
        return Transaction(message.get("transaction_id"), message.get("is_sender_buyer"), message.get("counterparty"), message.get("amount"), message.get("quantities_by_good_pbk"), sender)

    def matches(self, other: 'Transaction') -> bool:
        """
        Check if the transaction matches with another (mirroring) transaction.

        Two transaction requests do match if:
        - the transaction id is the same;
        - one of them is from a buyer and the other one is from a seller
        - the counterparty and the origin field are consistent.
        - the amount and the quantities are equal.

        :param other: the other transaction to match.
        :return: True if the two
        """
        result = True
        result = result and self.transaction_id == other.transaction_id
        result = result and self.is_sender_buyer != other.is_sender_buyer
        result = result and self.counterparty == other.sender
        result = result and other.counterparty == self.sender
        result = result and self.amount == other.amount
        result = result and self.quantities_by_good_pbk == other.quantities_by_good_pbk

        return result


class GameData:
    """Convenience representation of the game data."""

    def __init__(self, sender: Address, money: float, endowment: List[int], utility_params: List[float],
                 nb_agents: int, nb_goods: int, tx_fee: float, agent_pbk_to_name: Dict[str, str], good_pbk_to_name: Dict[str, str]) -> None:
        """
        Initialize a game data object.

        :param sender: the sender
        :param money: the money amount.
        :param endowment: the endowment for every good.
        :param utility_params: the utility params for every good.
        :param nb_agents: the number of agents.
        :param nb_goods: the number of goods.
        :param tx_fee: the transaction fee.
        :param agent_pbk_to_name: the mapping from the public keys to the names of the agents.
        :param good_pbk_to_name: the mapping from the public keys to the names of the goods.
        :return: None
        """
        assert len(endowment) == len(utility_params)
        self.sender = sender
        self.money = money
        self.endowment = endowment
        self.utility_params = utility_params
        self.nb_agents = nb_agents
        self.nb_goods = nb_goods
        self.tx_fee = tx_fee
        self.agent_pbk_to_name = agent_pbk_to_name
        self.good_pbk_to_name = good_pbk_to_name

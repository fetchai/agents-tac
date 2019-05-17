# -*- coding: utf-8 -*-

# ------------------------------------------------------------------------------
#
#   Copyright 2018-2019 Fetch.AI Limited
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------

"""Schemas for the protocol to communicate with the controller."""
import copy
import logging
import pprint
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Dict, Any
from typing import Optional

import google
from google.protobuf.message import DecodeError

import tac.tac_pb2 as tac_pb2
from tac.helpers.misc import TacError

from oef.schema import Description

logger = logging.getLogger(__name__)


def _make_str_int_pair(key: str, value: int) -> tac_pb2.StrIntPair:
    """
    Helper method to make a Protobuf StrIntPair.
    :param key: the first element of the pair.
    :param value: the second element of the pair.
    :return: a StrIntPair protobuf object.
    """
    pair = tac_pb2.StrIntPair()
    pair.first = key
    pair.second = value
    return pair


class ErrorCode(Enum):
    GENERIC_ERROR = 0
    REQUEST_NOT_VALID = 1
    AGENT_ALREADY_REGISTERED = 2
    AGENT_NOT_REGISTERED = 3
    TRANSACTION_NOT_VALID = 4


class Message(ABC):
    """Abstract class representing a message between TAC agents and TAC controller."""

    @classmethod
    @abstractmethod
    def from_pb(cls, obj):
        """From Protobuf to :class:`~tac.protocol.Message` object"""

    @abstractmethod
    def to_pb(self):
        """From :class:`~tac.protocol.Message` to Protobuf object"""

    def serialize(self) -> bytes:
        """Serialize the message."""
        return self.to_pb().SerializeToString()

    def _build_str(self, **kwargs) -> str:
        return type(self).__name__ + "({})".format(pprint.pformat(kwargs))

    def __str__(self):
        return self._build_str()


class Request(Message, ABC):
    """Message from clients to controller"""

    @classmethod
    def from_pb(cls, obj: bytes) -> 'Request':
        """
        Parse a string of bytes associated to a request message to the TAC controller.
        :param obj: the string of bytes to be parsed.
        :param public_key: the public key of the request sender.
        :return: a :class:`~tac.protocol.Response` object.
        :raises TacError: if the string of bytes cannot be parsed as a Response from the TAC Controller.
        """

        msg = tac_pb2.TACAgent.Message()
        msg.ParseFromString(obj)
        case = msg.WhichOneof("msg")
        if case == "register":
            return Register()
        elif case == "unregister":
            return Unregister()
        elif case == "transaction":
            return Transaction.from_pb(obj)
        else:
            raise TacError("Unrecognized type of Request.")

    def to_pb(self):
        raise NotImplementedError

    def __eq__(self, other):
        return type(self) == type(other)


class Register(Request):
    """Message to register an agent to the competition."""

    def to_pb(self) -> tac_pb2.TACAgent.Message:
        msg = tac_pb2.TACAgent.Register()
        envelope = tac_pb2.TACAgent.Message()
        envelope.register.CopyFrom(msg)
        return envelope


class Unregister(Request):
    """Message to unregister an agent from the competition."""

    def to_pb(self) -> tac_pb2.TACAgent.Message:
        msg = tac_pb2.TACAgent.Unregister()
        envelope = tac_pb2.TACAgent.Message()
        envelope.unregister.CopyFrom(msg)
        return envelope


class Transaction(Request):

    def __init__(self, transaction_id: str, buyer: bool, counterparty: str,
                 amount: int, quantities_by_good_pbk: Dict[str, int], sender: Optional[str] = None):
        """
        A transaction request.

        :param transaction_id: the id of the transaction.
        :param buyer: whether the transaction request is sent by a buyer.
        :param sender: the sender of the transaction request.
        :param counterparty: the counterparty of the transaction.
        :param amount: the amount of money involved.
        :param quantities_by_good_pbk: a map from good pbk to the quantity of that good involved in the transaction.
        """
        self.transaction_id = transaction_id
        self.buyer = buyer
        self.counterparty = counterparty
        self.amount = amount
        self.quantities_by_good_pbk = quantities_by_good_pbk

        self.sender = sender

    def to_pb(self) -> tac_pb2.TACAgent.Message:
        msg = tac_pb2.TACAgent.Transaction()
        msg.transaction_id = self.transaction_id
        msg.buyer = self.buyer
        msg.counterparty = self.counterparty
        msg.amount = self.amount

        good_pbk_quantity_pairs = [_make_str_int_pair(good_pbk, quantity) for good_pbk, quantity in self.quantities_by_good_pbk.items()]
        msg.quantities.extend(good_pbk_quantity_pairs)

        envelope = tac_pb2.TACAgent.Message()
        envelope.transaction.CopyFrom(msg)
        return envelope

    @classmethod
    def from_pb(cls, obj: bytes) -> 'Request':
        msg = tac_pb2.TACAgent.Message()
        msg.ParseFromString(obj)

        quantities_per_good_pbk = {pair.first: pair.second for pair in msg.transaction.quantities}

        return Transaction(msg.transaction.transaction_id,
                           msg.transaction.buyer,
                           msg.transaction.counterparty,
                           msg.transaction.amount,
                           quantities_per_good_pbk)

    def from_proposal(self, proposal: Description, transaction_id: str,
                      is_buyer: bool, counterparty: str) -> 'Request':
        """
        Create a transaction from a proposal.

        :param proposal:
        :param transaction_id:
        :param is_buyer:
        :param counterparty:
        :return: Transaction
        """
        data = copy.deepcopy(proposal.values)
        price = data.pop("price")
        quantity_by_good_pbk = {key: value for key, value in data.items()}
        return Transaction(transaction_id, is_buyer, counterparty, price, quantity_by_good_pbk,
                           sender=self.public_key)

    def matches(self, other: 'Transaction') -> bool:
        """
        Check if the transaction matches with another transaction request.

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
        result = result and self.buyer != other.buyer
        result = result and self.counterparty == other.sender
        result = result and other.counterparty == self.sender
        result = result and self.amount == other.amount
        result = result and self.quantities_by_good_pbk == other.quantities_by_good_pbk

        return result

    def __str__(self):
        return self._build_str(
            transaction_id=self.transaction_id,
            buyer=self.buyer,
            counterparty=self.counterparty,
            amount=self.amount,
            good_pbk_quantity_pairs=self.quantities_by_good_pbk
        )


class Response(Message):
    """Message from controller to clients"""

    @classmethod
    def from_pb(cls, obj: bytes) -> 'Response':
        """
        Parse a string of bytes associated to a response message from the TAC controller.
        :param obj: the string of bytes to be parsed.
        :return: a :class:`~tac.protocol.Response` object.
        :raises TacError: if the string of bytes cannot be parsed as a Response from the TAC Controller.
        """

        try:
            msg = tac_pb2.TACController.Message()
            msg.ParseFromString(obj)
            case = msg.WhichOneof("msg")
            if case == "registered":
                return Registered()
            elif case == "unregistered":
                return Unregistered()
            elif case == "cancelled":
                return Cancelled()
            elif case == "game_data":
                return GameData(msg.game_data.money,
                                list(msg.game_data.endowment),
                                list(msg.game_data.utility_params),
                                msg.game_data.nb_agents,
                                msg.game_data.nb_goods,
                                msg.game_data.tx_fee,
                                msg.game_data.agent_pbks,
                                msg.game_data.good_pbks)
            elif case == "tx_confirmation":
                return TransactionConfirmation(msg.tx_confirmation.transaction_id)
            elif case == "error":
                error_code = ErrorCode(msg.error.error_code)
                error_msg = msg.error.error_msg
                details = dict(msg.error.details.items())
                return Error(error_code, error_msg, details)
            else:
                raise TacError("Unrecognized type of Response.")
        except DecodeError as e:
            logger.exception(str(e))
            raise TacError("Error in decoding the message.")

    def to_pb(self) -> tac_pb2.TACController.Message:
        raise NotImplementedError

    def __eq__(self, other):
        return type(self) == type(other)


class Registered(Response):
    """This response from the TAC Controller means that the agent has been registered to the TAC."""

    def to_pb(self) -> tac_pb2.TACController.Message:
        msg = tac_pb2.TACController.Registered()
        envelope = tac_pb2.TACController.Message()
        envelope.registered.CopyFrom(msg)
        return envelope


class Unregistered(Response):
    """This response from the TAC Controller means that the agent has been unregistered from the TAC."""

    def to_pb(self) -> tac_pb2.TACController.Message:
        msg = tac_pb2.TACController.Unregistered()
        envelope = tac_pb2.TACController.Message()
        envelope.unregistered.CopyFrom(msg)
        return envelope


class Cancelled(Response):
    """This response means that the competition to which the agent was registered has been cancelled."""

    def to_pb(self) -> tac_pb2.TACController.Message:
        msg = tac_pb2.TACController.Cancelled()
        envelope = tac_pb2.TACController.Message()
        envelope.cancelled.CopyFrom(msg)
        return envelope


class Error(Response):
    """This response means that something bad happened while processing a request."""

    def __init__(self, error_code: ErrorCode, error_msg: str, details: Optional[Dict[str, Any]] = None):
        self.error_code = error_code
        self.error_msg = error_msg
        self.details = details if details is not None else {}

    def to_pb(self) -> tac_pb2.TACController.Message:
        msg = tac_pb2.TACController.Error()
        msg.error_code = self.error_code.value
        msg.error_msg = self.error_msg
        msg.details.update(self.details)
        envelope = tac_pb2.TACController.Message()
        envelope.error.CopyFrom(msg)
        return envelope

    def __str__(self):
        return self._build_str(error_msg=self.error_msg)

    def __eq__(self, other):
        return super().__eq__(other) and self.error_msg == other.error_msg


class GameData(Response):
    """Class that holds the game configuration and the initialization of a TAC agent."""

    def __init__(self, money: int, endowment: List[int], utility_params: List[float], nb_agents: int, nb_goods: int,
                 tx_fee: float, agent_pbks: List[str], good_pbks: List[str]):
        """
        Initialize a game data object.
        :param money: the money amount.
        :param endowment: the endowment for every good.
        :param utility_params: the utility params for every good.
        :param nb_agents: the number of agents.
        :param nb_goods: the number of goods.
        :param tx_fee: the transaction fee.
        :param agent_pbks: the pbks of the agents.
        :param good_pbks: the pbks of the goods.
        """
        assert len(endowment) == len(utility_params)
        self.money = money
        self.endowment = endowment
        self.utility_params = utility_params
        self.nb_agents = nb_agents
        self.nb_goods = nb_goods
        self.tx_fee = tx_fee
        self.agent_pbks = agent_pbks
        self.good_pbks = good_pbks

    def to_pb(self) -> tac_pb2.TACController.Message:
        msg = tac_pb2.TACController.GameData()
        msg.money = self.money
        msg.endowment.extend(self.endowment)
        msg.utility_params.extend(self.utility_params)
        msg.nb_agents = self.nb_agents
        msg.nb_goods = self.nb_goods
        msg.tx_fee = self.tx_fee
        msg.agent_pbks.extend(self.agent_pbks)
        msg.good_pbks.extend(self.good_pbks)
        envelope = tac_pb2.TACController.Message()
        envelope.game_data.CopyFrom(msg)
        return envelope

    def __str__(self):
        return self._build_str(
            money=self.money,
            endowment=self.endowment,
            utility_params=self.utility_params,
            nb_agents=self.nb_agents,
            nb_goods=self.nb_goods,
            tx_fee=self.tx_fee,
            agent_pbks=self.agent_pbks,
            good_pbks=self.good_pbks
        )

    def __eq__(self, other):
        return super().__eq__(other) and \
            self.money == other.money and \
            self.endowment == other.endowment and \
            self.utility_params == other.utility_params and \
            self.nb_agents == other.nb_agents and \
            self.nb_goods == other.nb_goods and \
            self.tx_fee == other.tx_fee and \
            self.agent_pbks == other.agent_pbks and \
            self.good_pbks == other.good_pbks


class TransactionConfirmation(Response):

    def __init__(self, transaction_id: str):
        self.transaction_id = transaction_id

    def to_pb(self) -> tac_pb2.TACController.Message:
        msg = tac_pb2.TACController.TransactionConfirmation()
        msg.transaction_id = self.transaction_id
        envelope = tac_pb2.TACController.Message()
        envelope.tx_confirmation.CopyFrom(msg)
        return envelope

    def __str__(self):
        return self._build_str(transaction_id=self.transaction_id)

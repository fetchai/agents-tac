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
import logging
import pprint
from abc import ABC, abstractmethod
from typing import List, Dict

from google.protobuf.message import DecodeError

import tac.tac_pb2 as tac_pb2
from tac.helpers.misc import TacError

logger = logging.getLogger(__name__)


def _make_int_pair(key: int, value: int) -> tac_pb2.IntPair:
    """
    Helper method to make a Protobuf IntPair.
    :param key: the first element of the pair.
    :param value: the second element of the pair.
    :return: a IntPair protobuf object.
    """
    pair = tac_pb2.IntPair()
    pair.key = key
    pair.value = value
    return pair


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
                 amount: int, quantities_by_good_id: Dict[int, int]):
        """
        A transaction request.

        :param transaction_id: the id of the transaction.
        :param buyer: whether the transaction request is sent by a buyer.
        :param counterparty: the counterparty of the transaction.
        :param amount: the amount of money involved.
        :param quantities_by_good_id: a map from good id to the quantity of that good involved in the transaction.
        """
        self.transaction_id = transaction_id
        self.buyer = buyer
        self.counterparty = counterparty
        self.amount = amount
        self.quantities_by_good_id = quantities_by_good_id

    def to_pb(self) -> tac_pb2.TACAgent.Message:
        msg = tac_pb2.TACAgent.Transaction()
        msg.transaction_id = self.transaction_id
        msg.buyer = self.buyer
        msg.counterparty = self.counterparty
        msg.amount = self.amount

        good_id_quantity_pairs = [_make_int_pair(gid, q) for gid, q in self.quantities_by_good_id.items()]
        dictionary = tac_pb2.Dictionary()
        dictionary.pairs.extend(good_id_quantity_pairs)
        msg.quantities.CopyFrom(dictionary)

        envelope = tac_pb2.TACAgent.Message()
        envelope.transaction.CopyFrom(msg)
        return envelope

    @classmethod
    def from_pb(cls, obj: bytes) -> 'Request':
        msg = tac_pb2.TACAgent.Message()
        msg.ParseFromString(obj)

        quantities_per_good_id = {pair.key: pair.value for pair in msg.transaction.quantities.pairs}

        return Transaction(msg.transaction.transaction_id,
                           msg.transaction.buyer,
                           msg.transaction.counterparty,
                           msg.transaction.amount,
                           quantities_per_good_id)

    def __str__(self):
        return self._build_str(
            transaction_id=self.transaction_id,
            buyer=self.buyer,
            counterparty=self.counterparty,
            amount=self.amount,
            good_id_quantity_pairs=self.quantities_by_good_id
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
            elif case == "game_data":
                return GameData(msg.game_data.money,
                                list(msg.game_data.resources),
                                list(msg.game_data.preferences),
                                msg.game_data.fee)
            elif case == "tx_confirmation":
                return TransactionConfirmation(msg.tx_confirmation.transaction_id)
            elif case == "error":
                error_msg = msg.error.error_msg
                return Error(error_msg)
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


class Error(Response):
    """This response means that something bad happened while processing a request."""

    def __init__(self, error_msg: str):
        self.error_msg = error_msg

    def to_pb(self) -> tac_pb2.TACController.Message:
        msg = tac_pb2.TACController.Error()
        msg.error_msg = self.error_msg
        envelope = tac_pb2.TACController.Message()
        envelope.error.CopyFrom(msg)
        return envelope

    def __str__(self):
        return self._build_str(error_msg=self.error_msg)

    def __eq__(self, other):
        return super().__eq__(other) and self.error_msg == other.error_msg


class GameData(Response):
    """Class that holds the initial condition of a TAC agent."""

    def __init__(self, money: int, endowment: List[int], preferences: List[int], fee: int):
        """
        Initialize a game data object.
        :param money: the money amount.
        :param endowment: the endowment for every good.
        :param preferences: the utilities for every good.
        :param fee: the transaction fee.
        """
        assert len(endowment) == len(preferences)
        self.money = money
        self.endowment = endowment
        self.preferences = preferences
        self.fee = fee

    def to_pb(self) -> tac_pb2.TACController.Message:
        msg = tac_pb2.TACController.GameData()
        msg.money = self.money
        msg.resources.extend(self.endowment)
        msg.preferences.extend(self.preferences)
        msg.fee = self.fee
        envelope = tac_pb2.TACController.Message()
        envelope.game_data.CopyFrom(msg)
        return envelope

    def __str__(self):
        return self._build_str(
            money=self.money,
            endowment=self.endowment,
            preferences=self.preferences,
            fee=self.fee
        )

    def __eq__(self, other):
        return super().__eq__(other) and \
            self.money == other.money and \
            self.endowment == other.endowment and \
            self.preferences == other.preferences and \
            self.fee == other.fee


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

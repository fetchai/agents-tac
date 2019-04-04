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
from enum import Enum
from typing import List

from google.protobuf.message import DecodeError

import tac.tac_pb2 as tac_pb2

logger = logging.getLogger(__name__)


class Message(ABC):
    """Abstract class representing a message between TAC agents and TAC controller."""

    @classmethod
    @abstractmethod
    def from_pb(cls, obj):
        """From Protobuf to 'Message' object"""

    @abstractmethod
    def to_pb(self):
        """From 'Message' to Protobuf object"""

    def serialize(self) -> bytes:
        """Serialize the message."""
        return self.to_pb().SerializeToString()

    def _build_str(self, **kwargs) -> str:
        return type(self).__name__ + "({})".format(pprint.pformat(kwargs))

    def __str__(self):
        return self._build_str()


class Request(Message, ABC):
    """Message from clients to controller"""

    def __init__(self, public_key: str):
        super().__init__()
        self.public_key = public_key

    @classmethod
    def from_pb(cls, obj: bytes, public_key: str = "") -> 'Request':
        msg = tac_pb2.TACAgent.Message()
        msg.ParseFromString(obj)
        case = msg.WhichOneof("msg")
        if case == "register":
            return Register(public_key)
        elif case == "unregister":
            return Unregister(public_key)
        elif case == "transaction":
            return Transaction(public_key, msg.transaction.transaction_id, msg.transaction.buyer,
                               msg.transaction.counterparty, msg.transaction.amount,
                               msg.transaction.good_ids, msg.transaction.quantities)
        else:
            raise Exception("Unrecognized type of Response.")

    def to_pb(self):
        raise NotImplementedError


class Register(Request):
    """Message to register an agent to the competition."""

    def to_pb(self) -> tac_pb2.TACAgent.Message:
        msg = tac_pb2.TACAgent.Register()
        envelope = tac_pb2.TACAgent.Message()
        envelope.register.CopyFrom(msg)
        return envelope


class Unregister(Request):
    """Message to register an agent to the competition."""

    def to_pb(self) -> tac_pb2.TACAgent.Message:
        msg = tac_pb2.TACAgent.Unregister()
        envelope = tac_pb2.TACAgent.Message()
        envelope.unregister.CopyFrom(msg)
        return envelope


class Transaction(Request):

    def __init__(self, public_key: str, transaction_id: str, buyer: bool, counterparty: str,
                 amount: int, good_ids: List[int], quantities: List[int]):
        """

        :param public_key: the public key of the sender.
        :param buyer: whether the transaction request is sent by a buyer.
        :param counterparty: the counterparty of the transaction.
        :param amount: the amount of money involved.
        :param good_ids: the good identifiers.
        :param quantities: the quantities of the good to be transacted.
        """
        super().__init__(public_key)
        self.transaction_id = transaction_id
        self.buyer = buyer
        self.counterparty = counterparty
        self.amount = amount
        self.good_ids = good_ids
        self.quantities = quantities
        assert len(self.good_ids) == len(quantities)

    def to_pb(self) -> tac_pb2.TACAgent.Message:
        msg = tac_pb2.TACAgent.Transaction()
        msg.transaction_id = self.transaction_id
        msg.buyer = self.buyer
        msg.counterparty = self.counterparty
        msg.amount = self.amount
        msg.good_ids.extend(self.good_ids)
        msg.quantities.extend(self.quantities)
        envelope = tac_pb2.TACAgent.Message()
        envelope.transaction.CopyFrom(msg)
        return envelope

    def __str__(self):
        return self._build_str(
            transaction_id=self.transaction_id,
            buyer=self.buyer,
            counterparty=self.counterparty,
            amount=self.amount,
            good_ids=self.good_ids,
            quantities=self.quantities
        )


class Response(Message):
    """Message from controller to clients"""

    @classmethod
    def from_pb(cls, obj: bytes) -> 'Response':
        try:
            msg = tac_pb2.TACController.Message()
            msg.ParseFromString(obj)
            case = msg.WhichOneof("msg")
            if case == "registered":
                return Registered()
            elif case == "unregistered":
                return Unregistered()
            elif case == "game_data":
                return GameData(msg.game_data.money, msg.game_data.resources,
                                msg.game_data.preferences, msg.game_data.scores, msg.game_data.fee)
            elif case == "tx_confirmation":
                return TransactionConfirmation(msg.tx_confirmation.transaction_id)
            elif case == "error":
                error_msg = msg.error.error_msg
                return Error(error_msg)
            else:
                raise Exception("Unrecognized type of Response.")
        except DecodeError as e:
            logger.exception(str(e))

    def to_pb(self) -> tac_pb2.TACController.Message:
        raise NotImplementedError


class Registered(Response):

    def to_pb(self) -> tac_pb2.TACController.Message:
        msg = tac_pb2.TACController.Registered()
        envelope = tac_pb2.TACController.Message()
        envelope.registered.CopyFrom(msg)
        return envelope


class Unregistered(Response):

    def to_pb(self) -> tac_pb2.TACController.Message:
        msg = tac_pb2.TACController.Unregistered()
        envelope = tac_pb2.TACController.Message()
        envelope.unregistered.CopyFrom(msg)
        return envelope


class Error(Response):

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


class GameData(Response):

    def __init__(self, money: int, endowment: List[int], preference: List[int], scores: List[int], fee: int):
        self.money = money
        self.endowment = endowment
        self.preference = preference
        self.scores = scores
        self.fee = fee

    def to_pb(self) -> tac_pb2.TACController.Message:
        msg = tac_pb2.TACController.GameData()
        msg.money = self.money
        msg.resources.extend(self.endowment)
        msg.preferences.extend(self.preference)
        msg.scores.extend(self.scores)
        msg.fee = self.fee
        envelope = tac_pb2.TACController.Message()
        envelope.game_data.CopyFrom(msg)
        return envelope

    def __str__(self):
        return self._build_str(
            money=self.money,
            endowment=self.endowment,
            preference=self.preference,
            scores=self.scores,
            fee=self.fee
        )


class TransactionConfirmation(Response):

    def __init__(self, transaction_id: int):
        self.transaction_id = transaction_id

    def to_pb(self) -> tac_pb2.TACController.Message:
        msg = tac_pb2.TACController.TransactionConfirmation()
        msg.transaction_id = self.transaction_id
        envelope = tac_pb2.TACController.Message()
        envelope.tx_confirmation.CopyFrom(msg)
        return envelope

    def __str__(self):
        return self._build_str(transaction_id=self.transaction_id)

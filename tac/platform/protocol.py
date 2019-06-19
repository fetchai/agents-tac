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

from google.protobuf.message import DecodeError

from tac.helpers.crypto import Crypto
from tac.helpers.misc import TacError
import tac.tac_pb2 as tac_pb2

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
    AGENT_PBK_ALREADY_REGISTERED = 2
    AGENT_NAME_ALREADY_REGISTERED = 3
    AGENT_NOT_REGISTERED = 4
    TRANSACTION_NOT_VALID = 5
    TRANSACTION_NOT_MATCHING = 6
    AGENT_NAME_NOT_IN_WHITELIST = 7


_from_ec_to_msg = {
    ErrorCode.GENERIC_ERROR: "Unexpected error.",
    ErrorCode.REQUEST_NOT_VALID: "Request not recognized",
    ErrorCode.AGENT_PBK_ALREADY_REGISTERED: "Agent pbk already registered.",
    ErrorCode.AGENT_NAME_ALREADY_REGISTERED: "Agent name already registered.",
    ErrorCode.AGENT_NOT_REGISTERED: "Agent not registered.",
    ErrorCode.TRANSACTION_NOT_VALID: "Error in checking transaction",
    ErrorCode.TRANSACTION_NOT_MATCHING: "The transaction request does not match with a previous transaction request with the same id.",
    ErrorCode.AGENT_NAME_NOT_IN_WHITELIST: "Agent name not in whitelist."
}  # type: Dict[ErrorCode, str]


class Message(ABC):
    """Abstract class representing a message between TAC agents and TAC controller."""

    def __init__(self, public_key: str, crypto: Crypto):
        """
        :param public_key: The public key of the TAC agent
        :param crypto: the Crypto object
        """
        self.public_key = public_key
        self.crypto = crypto

    @classmethod
    @abstractmethod
    def from_pb(cls, obj, public_key: str):
        """From Protobuf to :class:`~tac.protocol.Message` object"""

    @abstractmethod
    def to_pb(self):
        """From :class:`~tac.protocol.Message` to Protobuf object"""

    def serialize_message_part(self) -> bytes:
        """Serialize the message."""
        return self.to_pb().SerializeToString()

    def sign_message(self, message: bytes) -> bytes:
        """Sign a message."""
        return self.crypto.sign_data(message)

    def serialize(self) -> bytes:
        """
        Serialize the message
        :return: the signature bytes object
        """
        result = tac_pb2.TACAgent.SignedMessage()
        result.message = self.serialize_message_part()
        result.signature = self.sign_message(result.message)
        return result.SerializeToString()

    def _build_str(self, **kwargs) -> str:
        return type(self).__name__ + "({})".format(pprint.pformat(kwargs))

    def __str__(self):
        return self._build_str()


class Request(Message, ABC):
    """Message from client to controller"""

    @classmethod
    def from_pb(cls, obj, public_key: str, crypto: Crypto) -> 'Request':
        """
        Parse a string of bytes associated to a request message to the TAC controller.
        :param obj: the string of bytes to be parsed.
        :param public_key: the public key of the request sender.
        :param crypto: the Crypto object
        :return: a :class:`~tac.protocol.Response` object.
        :raises TacError: if the string of bytes cannot be parsed as a Response from the TAC Controller.
        """

        signed_msg = tac_pb2.TACAgent.SignedMessage()
        signed_msg.ParseFromString(obj)

        if crypto.is_confirmed_integrity(signed_msg.message, signed_msg.signature, public_key):
            msg = tac_pb2.TACAgent.Message()
            msg.ParseFromString(signed_msg.message)
            case = msg.WhichOneof("msg")
            if case == "register":
                return Register.from_pb(msg.register, public_key, crypto)
            elif case == "unregister":
                return Unregister(public_key, crypto)
            elif case == "transaction":
                return Transaction.from_pb(msg.transaction, public_key, crypto)
            elif case == "get_state_update":
                return GetStateUpdate(public_key, crypto)
            else:
                raise TacError("Unrecognized type of Request.")
        else:
            raise ValueError("Bad signature. Do not trust!")

    def to_pb(self):
        raise NotImplementedError

    def __eq__(self, other):
        return type(self) == type(other)


class Register(Request):
    """Message to register an agent to the competition."""

    def __init__(self, public_key: str, crypto: Crypto, agent_name: str):
        """
        A registration message.

        :param public_key: the public key of the agent
        :param agent_name: the name of the agent
        :param crypto: the Crypto object
        """
        super().__init__(public_key, crypto)
        self.agent_name = agent_name

    def to_pb(self) -> tac_pb2.TACAgent.Message:
        msg = tac_pb2.TACAgent.Register()
        msg.agent_name = self.agent_name
        envelope = tac_pb2.TACAgent.Message()
        envelope.register.CopyFrom(msg)
        return envelope

    @classmethod
    def from_pb(cls, obj: tac_pb2.TACAgent.Register, public_key: str, crypto: Crypto) -> 'Register':
        return Register(public_key, crypto, obj.agent_name)


class Unregister(Request):
    """Message to unregister an agent from the competition."""

    def to_pb(self) -> tac_pb2.TACAgent.Message:
        msg = tac_pb2.TACAgent.Unregister()
        envelope = tac_pb2.TACAgent.Message()
        envelope.unregister.CopyFrom(msg)
        return envelope


class Transaction(Request):

    def __init__(self, transaction_id: str, buyer: bool, counterparty: str,
                 amount: float, quantities_by_good_pbk: Dict[str, int], sender: str, crypto: Crypto):
        """
        A transaction request.

        :param transaction_id: the id of the transaction.
        :param buyer: whether the transaction request is sent by a buyer.
        :param sender: the sender of the transaction request.
        :param counterparty: the counterparty of the transaction.
        :param amount: the amount of money involved.
        :param quantities_by_good_pbk: a map from good pbk to the quantity of that good involved in the transaction.
        """
        super().__init__(sender, crypto)
        self.transaction_id = transaction_id
        self.buyer = buyer
        self.counterparty = counterparty
        self.amount = amount
        self.quantities_by_good_pbk = quantities_by_good_pbk

    @property
    def sender(self):
        return self.public_key

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
    def from_pb(cls, obj: tac_pb2.TACAgent.Transaction, public_key: str, crypto: Crypto) -> 'Transaction':
        quantities_per_good_pbk = {pair.first: pair.second for pair in obj.quantities}

        return Transaction(obj.transaction_id,
                           obj.buyer,
                           obj.counterparty,
                           obj.amount,
                           quantities_per_good_pbk,
                           public_key,
                           crypto)

    @classmethod
    def from_proposal(cls, proposal: Description, transaction_id: str,
                      is_buyer: bool, counterparty: str, sender: str, crypto: Crypto) -> 'Transaction':
        """
        Create a transaction from a proposal.

        :param proposal:
        :param transaction_id:
        :param is_buyer:
        :param counterparty:
        :param sender:
        :param crypto:
        :return: Transaction
        """
        data = copy.deepcopy(proposal.values)
        price = data.pop("price")
        quantity_by_good_pbk = {key: value for key, value in data.items()}
        return Transaction(transaction_id, is_buyer, counterparty, price, quantity_by_good_pbk,
                           sender=sender, crypto=crypto)

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

    def __eq__(self, other):
        if type(self) != type(other):
            return False
        return self.transaction_id == other.transaction_id and \
            self.buyer == other.buyer and \
            self.counterparty == other.counterparty and \
            self.amount == other.amount and \
            self.quantities_by_good_pbk == other.quantities_by_good_pbk


class GetStateUpdate(Request):
    """Message to request an agent state update from the controller."""

    def to_pb(self) -> tac_pb2.TACAgent.Message:
        msg = tac_pb2.TACAgent.GetStateUpdate()
        envelope = tac_pb2.TACAgent.Message()
        envelope.get_state_update.CopyFrom(msg)
        return envelope


class Response(Message):
    """Message from controller to clients"""

    @classmethod
    def from_pb(cls, obj, public_key: str, crypto: Crypto) -> 'Response':
        """
        Parse a string of bytes associated to a response message from the TAC controller.
        :param obj: the string of bytes to be parsed.
        :param public_key: the public key of the recipient.
        :return: a :class:`~tac.protocol.Response` object.
        :raises TacError: if the string of bytes cannot be parsed as a Response from the TAC Controller.
        """

        try:
            signed_msg = tac_pb2.TACAgent.SignedMessage()
            signed_msg.ParseFromString(obj)

            if crypto.is_confirmed_integrity(signed_msg.message, signed_msg.signature, public_key):
                msg = tac_pb2.TACController.Message()
                msg.ParseFromString(signed_msg.message)
                case = msg.WhichOneof("msg")
                if case == "registered":
                    return Registered(public_key, crypto)
                elif case == "unregistered":
                    return Unregistered(public_key, crypto)
                elif case == "cancelled":
                    return Cancelled(public_key, crypto)
                elif case == "game_data":
                    return GameData.from_pb(msg.game_data, public_key, crypto)
                elif case == "tx_confirmation":
                    return TransactionConfirmation(public_key, crypto, msg.tx_confirmation.transaction_id)
                elif case == "state_update":
                    return StateUpdate.from_pb(msg.state_update, public_key, crypto)
                elif case == "error":
                    return Error.from_pb(msg.error, public_key, crypto)
                else:
                    raise TacError("Unrecognized type of Response.")
            else:
                raise ValueError("Bad signature. Do not trust!")
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

    def __init__(self, public_key: str, crypto: Crypto,
                 error_code: ErrorCode,
                 error_msg: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(public_key, crypto)
        self.error_code = error_code
        self.error_msg = _from_ec_to_msg[error_code] if error_msg is None else error_msg
        self.details = details if details is not None else {}

    def to_pb(self) -> tac_pb2.TACController.Message:
        msg = tac_pb2.TACController.Error()
        msg.error_code = self.error_code.value
        msg.error_msg = self.error_msg
        msg.details.update(self.details)
        envelope = tac_pb2.TACController.Message()
        envelope.error.CopyFrom(msg)
        return envelope

    @classmethod
    def from_pb(cls, obj, public_key: str, crypto: Crypto) -> 'Error':
        error_code = ErrorCode(obj.error_code)
        error_msg = obj.error_msg
        details = dict(obj.details.items())
        return Error(public_key, crypto, error_code, error_msg, details)

    def __str__(self):
        return self._build_str(error_msg=self.error_msg)

    def __eq__(self, other):
        return super().__eq__(other) and self.error_msg == other.error_msg


class GameData(Response):
    """Class that holds the game configuration and the initialization of a TAC agent."""

    def __init__(self, public_key: str, crypto: Crypto, money: int, endowment: List[int], utility_params: List[float],
                 nb_agents: int, nb_goods: int, tx_fee: float, agent_pbks: List[str], agent_names: List[str], good_pbks: List[str]):
        """
        Initialize a game data object.
        :param public_key: the destination
        :param th
        :param money: the money amount.
        :param endowment: the endowment for every good.
        :param utility_params: the utility params for every good.
        :param nb_agents: the number of agents.
        :param nb_goods: the number of goods.
        :param tx_fee: the transaction fee.
        :param agent_pbks: the pbks of the agents.
        :param agent_names: the names of the agents.
        :param good_pbks: the pbks of the goods.
        """
        assert len(endowment) == len(utility_params)
        super().__init__(public_key, crypto)
        self.money = money
        self.endowment = endowment
        self.utility_params = utility_params
        self.nb_agents = nb_agents
        self.nb_goods = nb_goods
        self.tx_fee = tx_fee
        self.agent_pbks = agent_pbks
        self.agent_names = agent_names
        self.good_pbks = good_pbks

    @classmethod
    def from_pb(cls, obj: tac_pb2.TACController.GameData, public_key: str, crypto: Crypto) -> 'GameData':
        return GameData(public_key,
                        crypto,
                        obj.money,
                        list(obj.endowment),
                        list(obj.utility_params),
                        obj.nb_agents,
                        obj.nb_goods,
                        obj.tx_fee,
                        obj.agent_pbks,
                        obj.agent_names,
                        obj.good_pbks)

    def to_pb(self) -> tac_pb2.TACController.Message:
        msg = tac_pb2.TACController.GameData()
        msg.money = self.money
        msg.endowment.extend(self.endowment)
        msg.utility_params.extend(self.utility_params)
        msg.nb_agents = self.nb_agents
        msg.nb_goods = self.nb_goods
        msg.tx_fee = self.tx_fee
        msg.agent_pbks.extend(self.agent_pbks)
        msg.agent_names.extend(self.agent_names)
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
            agent_names=self.agent_names,
            good_pbks=self.good_pbks
        )

    def __eq__(self, other):
        return type(self) == type(other) and \
            self.money == other.money and \
            self.endowment == other.endowment and \
            self.utility_params == other.utility_params and \
            self.nb_agents == other.nb_agents and \
            self.nb_goods == other.nb_goods and \
            self.tx_fee == other.tx_fee and \
            self.agent_pbks == other.agent_pbks and \
            self.agent_names == other.agent_names and \
            self.good_pbks == other.good_pbks


class TransactionConfirmation(Response):

    def __init__(self, public_key: str, crypto: Crypto, transaction_id: str):
        super().__init__(public_key, crypto)
        self.transaction_id = transaction_id

    def to_pb(self) -> tac_pb2.TACController.Message:
        msg = tac_pb2.TACController.TransactionConfirmation()
        msg.transaction_id = self.transaction_id
        envelope = tac_pb2.TACController.Message()
        envelope.tx_confirmation.CopyFrom(msg)
        return envelope

    def __str__(self):
        return self._build_str(transaction_id=self.transaction_id)


class StateUpdate(Response):

    def __init__(self, public_key: str,
                 crypto: Crypto,
                 initial_state: GameData,
                 transactions: List[Transaction]):
        super().__init__(public_key, crypto)
        self.initial_state = initial_state
        self.transactions = transactions

    def to_pb(self) -> tac_pb2.TACController.Message:
        msg = tac_pb2.TACController.StateUpdate()

        game_data = tac_pb2.TACController.GameData()
        game_data.money = self.initial_state.money
        game_data.endowment.extend(self.initial_state.endowment)
        game_data.utility_params.extend(self.initial_state.utility_params)
        game_data.nb_agents = self.initial_state.nb_agents
        game_data.nb_goods = self.initial_state.nb_goods
        game_data.tx_fee = self.initial_state.tx_fee
        game_data.agent_pbks.extend(self.initial_state.agent_pbks)
        game_data.agent_names.extend(self.initial_state.agent_names)
        game_data.good_pbks.extend(self.initial_state.good_pbks)

        msg.initial_state.CopyFrom(game_data)

        transactions = []
        for tx in self.transactions:
            tx_pb = tac_pb2.TACAgent.Transaction()
            tx_pb.transaction_id = tx.transaction_id
            tx_pb.buyer = tx.buyer
            tx_pb.counterparty = tx.counterparty
            tx_pb.amount = tx.amount

            good_pbk_quantity_pairs = [_make_str_int_pair(good_pbk, quantity) for good_pbk, quantity in
                                       tx.quantities_by_good_pbk.items()]
            tx_pb.quantities.extend(good_pbk_quantity_pairs)

            transactions.append(tx_pb)

        msg.txs.extend(transactions)

        envelope = tac_pb2.TACController.Message()
        envelope.state_update.CopyFrom(msg)
        return envelope

    @classmethod
    def from_pb(cls, obj, public_key: str, crypto: Crypto) -> 'StateUpdate':
        initial_state = GameData.from_pb(obj.initial_state, public_key, crypto)
        transactions = [Transaction.from_pb(tx_obj, public_key, crypto) for tx_obj in obj.txs]

        return StateUpdate(public_key,
                           crypto,
                           initial_state,
                           transactions)

    def __str__(self):
        return self._build_str(public_key=self.public_key)

    def __eq__(self, other):
        return type(self) == type(other) and \
            self.public_key == other.public_key and \
            self.crypto == other.crypto and \
            self.initial_state == other.initial_state and \
            self.transactions == other.transactions

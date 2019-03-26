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
import pprint
from abc import ABC, abstractmethod
from enum import Enum

import tac.tac_pb2 as tac_pb2


class Message(ABC):
    """Abstract class representing a message between TAC agents and TAC controller."""

    @classmethod
    @abstractmethod
    def from_pb(cls, obj):
        """From Protobuf to 'Message' object"""

    @abstractmethod
    def to_pb(self):
        """From 'Message' to Protobuf object"""

    def _build_str(self, **kwargs) -> str:
        return type(self).__name__ + "({})".format(pprint.pformat(kwargs))

    def __str__(self):
        return self._build_str()


class Request(Message, ABC):
    """Message from clients to controller"""

    @classmethod
    def from_pb(cls, obj: bytes, public_key: str = "") -> 'Request':
        msg = tac_pb2.TACAgent.Message()
        msg.ParseFromString(obj)
        case = msg.WhichOneof("msg")
        if case == "register":
            return Register(public_key)
        elif case == "unregister":
            return Unregister(public_key)
        else:
            raise Exception("Unrecognized type of Response.")

    def to_pb(self):
        raise NotImplementedError


class Register(Request):
    """Message to register an agent to the competition."""

    def __init__(self, public_key: str):
        super().__init__()
        self.public_key = public_key

    def to_pb(self) -> tac_pb2.TACAgent.Message:
        msg = tac_pb2.TACAgent.Register()
        envelope = tac_pb2.TACAgent.Message()
        envelope.register.CopyFrom(msg)
        return envelope


class Unregister(Request):
    """Message to register an agent to the competition."""

    def __init__(self, public_key: str):
        super().__init__()
        self.public_key = public_key

    def to_pb(self) -> tac_pb2.TACAgent.Message:
        msg = tac_pb2.TACAgent.Unregister()
        envelope = tac_pb2.TACAgent.Message()
        envelope.unregister.CopyFrom(msg)
        return envelope


class ResponseType(Enum):
    REGISTERED = "registered"
    UNREGISTERED = "unregistered"


class Response(Message):
    """Message from controller to clients"""

    @classmethod
    def from_pb(cls, obj: bytes) -> 'Response':
        msg = tac_pb2.TACController.Message()
        msg.ParseFromString(obj)
        case = msg.WhichOneof("msg")
        if case == "registered":
            return Registered()
        elif case == "unregistered":
            return Unregistered()
        elif case == "error":
            error_msg = msg.error.error_msg
            return Error(error_msg)
        else:
            raise Exception("Unrecognized type of Response.")

    def to_pb(self) -> tac_pb2.TACController.Message:
        raise NotImplementedError


class Registered(Response):

    def to_pb(self) -> tac_pb2.TACController.Registered:
        msg = tac_pb2.TACController.Registered()
        envelope = tac_pb2.TACController.Message()
        envelope.registered.CopyFrom(msg)
        return envelope


class Unregistered(Response):

    def to_pb(self) -> tac_pb2.TACController.Unregistered:
        msg = tac_pb2.TACController.Unregistered()
        envelope = tac_pb2.TACController.Message()
        envelope.unregistered.CopyFrom(msg)
        return envelope


class Error(Response):

    def __init__(self, error_msg: str):
        self.error_msg = error_msg

    def to_pb(self) -> tac_pb2.TACController.Error:
        msg = tac_pb2.TACController.Error()
        msg.error_msg = self.error_msg
        envelope = tac_pb2.TACController.Message()
        envelope.error.CopyFrom(msg)
        return msg

    def __str__(self):
        return self._build_str(error_msg=self.error_msg)

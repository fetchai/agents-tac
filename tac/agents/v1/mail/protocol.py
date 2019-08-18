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

"""Protocol module v2."""
import json
from abc import abstractmethod, ABC
from typing import List

from google.protobuf.struct_pb2 import Struct

from tac.agents.v1.mail.messages import Message
from tac.agents.v1.protocols import base_pb2


class Encoder(ABC):

    @abstractmethod
    def encode(self, msg: Message) -> bytes:
        """
        Encode a message.

        :param msg: the message to be encoded.
        :return: the encoded message.
        """


class Decoder(ABC):

    @abstractmethod
    def decode(self, obj: bytes) -> Message:
        """
        Decode a message.

        :param obj: the sequence of bytes to be decoded.
        :return: the decoded message.
        """


class Serializer(Encoder, Decoder, ABC):
    """The implementations of this class defines a serialization layer for a protocol."""


class DefaultProtobufSerializer(Serializer):
    """
    Default Protobuf serializer.

    It assumes that the Message contains a JSON-serializable body,
    and uses the Protobuf serialization for the Message objects."""

    def encode(self, msg: Message) -> bytes:

        msg_pb = base_pb2.Message()
        msg_pb.sender = msg.sender
        msg_pb.to = msg.to
        msg_pb.protocol_id = msg.protocol_id

        body_json = Struct()
        body_json.update(msg.body)
        body_bytes = body_json.SerializeToString()
        msg_pb.body = body_bytes

        msg_bytes = msg_pb.SerializeToString()
        return msg_bytes

    def decode(self, obj: bytes) -> Message:
        msg_pb = base_pb2.Message()
        msg_pb.ParseFromString(obj)

        body_json = Struct()
        body_json.ParseFromString(msg_pb.body)
        body = dict(body_json)
        msg = Message(to=msg_pb.to, sender=msg_pb.sender, protocol_id=msg_pb.protocol_id, **body)
        return msg


class DefaultJSONSerializer(Serializer):
    """Default serialization in JSON for the Message object."""

    def encode(self, msg: Message) -> bytes:
        json_msg = {
            "to": msg.to,
            "sender": msg.sender,
            "protocol_id": msg.protocol_id,
            "body": msg.body
        }

        bytes_msg = json.dumps(json_msg).encode("utf-8")
        return bytes_msg

    def decode(self, obj: bytes) -> Message:
        json_msg = json.loads(obj.decode("utf-8"))

        msg = Message(
            to=json_msg["to"],
            sender=json_msg["sender"],
            protocol_id=json_msg["protocol_id"],
            body=json_msg["body"]
        )

        return msg


class Protocol:

    def __init__(self, serializer: Serializer):
        """
        Define a protocol.

        :param serializer: the serialization layer.
        """
        self.serializer = serializer

    @abstractmethod
    def is_message_valid(self, msg: Message):
        """Determine whether a message is valid."""

    @abstractmethod
    def is_trace_valid(self, trace: List[Message]) -> bool:
        """Determine whether a sequence of messages follows the protocol."""

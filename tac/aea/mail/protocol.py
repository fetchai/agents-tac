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
from typing import List, Optional

from google.protobuf.struct_pb2 import Struct

from tac.aea.mail.messages import Message, Address, ProtocolId
from tac.aea.protocols import base_pb2


class Encoder(ABC):
    """Encoder interface."""

    @abstractmethod
    def encode(self, msg: Message) -> bytes:
        """
        Encode a message.

        :param msg: the message to be encoded.
        :return: the encoded message.
        """


class Decoder(ABC):
    """Decoder interface."""

    @abstractmethod
    def decode(self, obj: bytes) -> Message:
        """
        Decode a message.

        :param obj: the sequence of bytes to be decoded.
        :return: the decoded message.
        """


class Serializer(Encoder, Decoder, ABC):
    """The implementations of this class defines a serialization layer for a protocol."""


class ProtobufSerializer(Serializer):
    """
    Default Protobuf serializer.

    It assumes that the Message contains a JSON-serializable body.
    """

    def encode(self, msg: Message) -> bytes:
        """Encode a message into bytes using Protobuf."""
        body_json = Struct()
        body_json.update(msg.body)
        body_bytes = body_json.SerializeToString()
        return body_bytes

    def decode(self, obj: bytes) -> Message:
        """Decode bytes into a message using Protobuf."""
        body_json = Struct()
        body_json.ParseFromString(obj)

        body = dict(body_json)
        msg = Message(body=body)
        return msg


class JSONSerializer(Serializer):
    """Default serialization in JSON for the Message object."""

    def encode(self, msg: Message) -> bytes:
        """
        Encode a message into bytes using JSON format.

        :param msg: the message to be encoded.
        :return: the serialized message.
        """
        bytes_msg = json.dumps(msg.body).encode("utf-8")
        return bytes_msg

    def decode(self, obj: bytes) -> Message:
        """
        Decode bytes into a message using JSON.

        :param obj: the serialized message.
        :return: the decoded message.
        """
        json_msg = json.loads(obj.decode("utf-8"))
        return Message(json_msg)


class Envelope:
    """The message class."""

    def __init__(self, to: Optional[Address] = None,
                 sender: Optional[Address] = None,
                 protocol_id: Optional[ProtocolId] = None,
                 message: Optional[bytes] = b""):
        """
        Initialize a Message object.

        :param to: the public key of the receiver.
        :param sender: the public key of the sender.
        :param protocol_id: the protocol id.
        :param message: the protocol-specific message
        """
        self._to = to
        self._sender = sender
        self._protocol_id = protocol_id
        self._message = message
        assert type(self._to) == str or self._to is None
        try:
            if self._to is not None and type(self._to) == str:
                self._to.encode('utf-8')
        except Exception:
            assert False

    @property
    def to(self) -> Address:
        """Get public key of receiver."""
        return self._to

    @to.setter
    def to(self, to: Address) -> None:
        """Set public key of receiver."""
        self._to = to

    @property
    def sender(self) -> Address:
        """Get public key of sender."""
        return self._sender

    @sender.setter
    def sender(self, sender: Address) -> None:
        """Set public key of sender."""
        self._sender = sender

    @property
    def protocol_id(self) -> Optional[ProtocolId]:
        """Get protocol id."""
        return self._protocol_id

    @protocol_id.setter
    def protocol_id(self, protocol_id: ProtocolId) -> None:
        """Set the protocol id."""
        self._protocol_id = protocol_id

    @property
    def message(self) -> bytes:
        """Get the Message."""
        return self._message

    @message.setter
    def message(self, message: bytes) -> None:
        """Set the message."""
        self._message = message

    def __eq__(self, other):
        """Compare with another object."""
        return isinstance(other, Envelope) \
            and self.to == other.to \
            and self.sender == other.sender \
            and self.protocol_id == other.protocol_id \
            and self._message == other._message

    def encode(self) -> bytes:
        """
        Encode the envelope.

        :return: the encoded envelope.
        """
        envelope = self
        envelope_pb = base_pb2.Envelope()
        if envelope.to is not None:
            envelope_pb.to = envelope.to
        if envelope.sender is not None:
            envelope_pb.sender = envelope.sender
        if envelope.protocol_id is not None:
            envelope_pb.protocol_id = envelope.protocol_id
        if envelope.message is not None:
            envelope_pb.message = envelope.message

        envelope_bytes = envelope_pb.SerializeToString()
        return envelope_bytes

    @classmethod
    def decode(cls, envelope_bytes: bytes) -> 'Envelope':
        """
        Decode the envelope.

        :param envelope_bytes: the bytes to be decoded.
        :return: the decoded envelope.
        """
        envelope_pb = base_pb2.Envelope()
        envelope_pb.ParseFromString(envelope_bytes)

        to = envelope_pb.to if envelope_pb.to else None
        sender = envelope_pb.sender if envelope_pb.sender else None
        protocol_id = envelope_pb.protocol_id if envelope_pb.protocol_id else None
        message = envelope_pb.message if envelope_pb.message else None

        envelope = Envelope(to=to, sender=sender, protocol_id=protocol_id, message=message)
        return envelope


class Protocol:
    """The class that implements a protocol."""

    def __init__(self, serializer: Serializer):
        """
        Define a protocol.

        :param serializer: the serialization layer.
        """
        self.serializer = serializer

    @abstractmethod
    def is_message_valid(self, envelope: Envelope):
        """Determine whether a message is valid."""

    @abstractmethod
    def is_trace_valid(self, trace: List[Envelope]) -> bool:
        """Determine whether a sequence of messages follows the protocol."""

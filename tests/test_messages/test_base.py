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

"""This module contains the tests of the messages module."""
from tac.aea.mail.messages import Message
from tac.aea.mail.protocol import DefaultProtobufSerializer, DefaultJSONSerializer, Envelope


class TestDefaultSerializations:
    """Test that the default serializations work."""

    @classmethod
    def setup_class(cls):
        """Set up the use case."""
        cls.message = Message(content="hello")
        cls.envelope = Envelope(to="receiver", sender="sender", protocol_id="my_own_protocol", message=cls.message)

    def test_default_protobuf_serialization(self):
        """Test that the default Protobuf serialization works."""
        envelope = self.envelope

        serializer = DefaultProtobufSerializer()
        envelope_bytes = envelope.encode(serializer)
        actual_envelope = Envelope.decode(envelope_bytes, serializer)
        expected_envelope = envelope

        assert expected_envelope == actual_envelope

    def test_default_json_serialization(self):
        """Test that the default JSON serialization works."""
        envelope = self.envelope

        serializer = DefaultJSONSerializer()
        envelope_bytes = envelope.encode(serializer)
        actual_envelope = Envelope.decode(envelope_bytes, serializer)
        expected_envelope = envelope

        assert expected_envelope == actual_envelope

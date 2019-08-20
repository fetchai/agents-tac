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
from tac.aea.mail.messages import SimpleMessage
from tac.aea.mail.protocol import Envelope
from tac.aea.protocols.simple.serialization import SimpleSerializer


def test_default_bytes_serialization():
    """Test that the serialization for the 'simple' protocol works for the BYTES message."""
    msg = SimpleMessage(type=SimpleMessage.Type.BYTES, content=b"hello")
    envelope = Envelope(to="receiver", sender="sender", protocol_id=SimpleMessage.protocol_id, message=msg)
    serializer = SimpleSerializer()

    envelope_bytes = envelope.encode(serializer)
    actual_envelope = Envelope.decode(envelope_bytes, serializer)
    expected_envelope = envelope

    assert expected_envelope == actual_envelope


def test_default_error_serialization():
    """Test that the serialization for the 'simple' protocol works for the ERROR message."""
    msg = SimpleMessage(type=SimpleMessage.Type.ERROR, error_code=-1, error_msg="An error")
    envelope = Envelope(to="receiver", sender="sender", protocol_id=SimpleMessage.protocol_id, message=msg)
    serializer = SimpleSerializer()

    envelope_bytes = envelope.encode(serializer)
    actual_envelope = Envelope.decode(envelope_bytes, serializer)
    expected_envelope = envelope

    assert expected_envelope == actual_envelope

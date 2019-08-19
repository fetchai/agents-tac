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

"""This module contains the tests for the FIPA protocol."""
from tac.agents.v1.protocols.fipa.serialization import FIPASerializer
from tac.agents.v1.protocols.simple.serialization import SimpleSerializer

from tac.agents.v1.mail.messages import SimpleMessage, FIPAMessage
from tac.agents.v1.mail.protocol import DefaultProtobufSerializer, DefaultJSONSerializer, Envelope


def test_fipa_cfp_serialization():
    """Test that the serialization for the 'fipa' protocol works.."""
    msg = FIPAMessage(message_id=0, dialogue_id=0, target=0, performative=FIPAMessage.Performative.CFP,
                      query={"foo": "bar"})
    envelope = Envelope(to="receiver", sender="sender", protocol_id=FIPAMessage.protocol_id, message=msg)
    serializer = FIPASerializer()

    envelope_bytes = envelope.encode(serializer)

    actual_envelope = Envelope.decode(envelope_bytes, serializer)
    expected_envelope = envelope

    assert expected_envelope == actual_envelope

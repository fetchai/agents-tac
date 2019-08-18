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

from tac.agents.v1.mail.messages import Message, SimpleMessage, FIPAMessage
from tac.agents.v1.mail.protocol import DefaultProtobufSerializer, DefaultJSONSerializer


def test_fipa_cfp_serialization():
    """Test that the serialization for the 'fipa' protocol works.."""
    msg = FIPAMessage(to="receiver", sender="sender", message_id=0, dialogue_id=0, target=0,
                      performative=FIPAMessage.Performative.CFP, query={"foo": "bar"})
    msg_bytes = FIPASerializer().encode(msg)
    actual_msg = FIPASerializer().decode(msg_bytes)
    expected_msg = msg

    assert expected_msg == actual_msg

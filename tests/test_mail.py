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

"""This module contains tests for the mail module."""
import time

from tac.agents.v1.mail.messages import FIPAMessage, ByteMessage  # OEFMessage
from tac.agents.v1.mail.oef import OEFNetworkMailBox


def test_example(network_node):
    """Test the mailbox."""
    mailbox1 = OEFNetworkMailBox("mailbox1", "127.0.0.1", 10000)
    mailbox2 = OEFNetworkMailBox("mailbox2", "127.0.0.1", 10000)

    mailbox1.connect()
    mailbox2.connect()

    msg = ByteMessage("mailbox2", "mailbox1", message_id=0, dialogue_id=0, content=b"hello")
    mailbox1.send(msg)
    msg = FIPAMessage("mailbox2", "mailbox1", 0, 0, 0, FIPAMessage.Performative.CFP, query=None)
    mailbox1.send(msg)
    msg = FIPAMessage("mailbox2", "mailbox1", 0, 0, 0, FIPAMessage.Performative.PROPOSE, proposal=[])
    mailbox1.send(msg)
    msg = FIPAMessage("mailbox2", "mailbox1", 0, 0, 0, FIPAMessage.Performative.ACCEPT)
    mailbox1.send(msg)
    msg = FIPAMessage("mailbox2", "mailbox1", 0, 0, 0, FIPAMessage.Performative.DECLINE)
    mailbox1.send(msg)

    time.sleep(5.0)

    msg = mailbox2.inbox.get(block=True, timeout=1.0)
    assert msg.get("content") == b"hello"
    msg = mailbox2.inbox.get(block=True, timeout=1.0)
    assert msg.protocol_id == "fipa"
    assert msg.get("performative") == FIPAMessage.Performative.CFP
    msg = mailbox2.inbox.get(block=True, timeout=1.0)
    assert msg.protocol_id == "fipa"
    assert msg.get("performative") == FIPAMessage.Performative.PROPOSE
    msg = mailbox2.inbox.get(block=True, timeout=1.0)
    assert msg.protocol_id == "fipa"
    assert msg.get("performative") == FIPAMessage.Performative.ACCEPT
    msg = mailbox2.inbox.get(block=True, timeout=1.0)
    assert msg.protocol_id == "fipa"
    assert msg.get("performative") == FIPAMessage.Performative.DECLINE

    mailbox1.disconnect()
    mailbox2.disconnect()

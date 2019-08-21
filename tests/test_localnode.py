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

"""This module contains the tests of the local OEF node implementation."""
import asyncio
import time

from tac.aea.helpers.local_node import LocalNode, OEFLocalProxy
from tac.aea.mail.messages import DefaultMessage, FIPAMessage
from tac.aea.mail.oef import OEFMailBox


def test_connection():
    """Test that two mailbox can connect to the node."""
    with LocalNode() as node:
        mailbox1 = OEFMailBox(OEFLocalProxy("mailbox1", node, loop=asyncio.new_event_loop()))
        mailbox2 = OEFMailBox(OEFLocalProxy("mailbox2", node, loop=asyncio.new_event_loop()))

        mailbox1.connect()
        mailbox2.connect()

        mailbox1.disconnect()
        mailbox2.disconnect()


def test_communication():
    """Test that two mailbox can communicate through the node."""
    with LocalNode() as node:
        mailbox1 = OEFMailBox(OEFLocalProxy("mailbox1", node, loop=asyncio.new_event_loop()))
        mailbox2 = OEFMailBox(OEFLocalProxy("mailbox2", node, loop=asyncio.new_event_loop()))

        mailbox1.connect()
        mailbox2.connect()

        mailbox1.send(DefaultMessage("mailbox2", "mailbox1", type=DefaultMessage.Type.BYTES, content=b"hello"))
        mailbox1.send(FIPAMessage("mailbox2", "mailbox1", 0, 0, 0, FIPAMessage.Performative.CFP, query=None))
        mailbox1.send(FIPAMessage("mailbox2", "mailbox1", 0, 0, 0, FIPAMessage.Performative.PROPOSE, proposal=[]))
        mailbox1.send(FIPAMessage("mailbox2", "mailbox1", 0, 0, 0, FIPAMessage.Performative.ACCEPT))
        mailbox1.send(FIPAMessage("mailbox2", "mailbox1", 0, 0, 0, FIPAMessage.Performative.DECLINE))

        time.sleep(1.0)

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

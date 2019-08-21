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

from tac.aea.helpers.local_node import LocalNode, OEFLocalConnection
from tac.aea.mail.base import MailBox
from tac.aea.mail.messages import DefaultMessage, FIPAMessage
from tac.aea.mail.oef import OEFMailBox
from tac.aea.mail.protocol import Envelope
from tac.aea.protocols.default.serialization import DefaultSerializer
from tac.aea.protocols.fipa.serialization import FIPASerializer


def test_connection():
    """Test that two mailbox can connect to the node."""
    with LocalNode() as node:
        mailbox1 = MailBox(OEFLocalConnection("mailbox1", node, loop=asyncio.new_event_loop()))
        mailbox2 = MailBox(OEFLocalConnection("mailbox2", node, loop=asyncio.new_event_loop()))

        mailbox1.connect()
        mailbox2.connect()

        mailbox1.disconnect()
        mailbox2.disconnect()


def test_communication():
    """Test that two mailbox can communicate through the node."""
    with LocalNode() as node:
        mailbox1 = MailBox(OEFLocalConnection("mailbox1", node, loop=asyncio.new_event_loop()))
        mailbox2 = MailBox(OEFLocalConnection("mailbox2", node, loop=asyncio.new_event_loop()))

        mailbox1.connect()
        mailbox2.connect()

        msg = DefaultMessage(type=DefaultMessage.Type.BYTES, content=b"hello")
        msg_bytes = DefaultSerializer().encode(msg)
        envelope = Envelope(to="mailbox2", sender="mailbox1", protocol_id=DefaultMessage.protocol_id, message=msg_bytes)
        mailbox1.send(envelope)

        msg = FIPAMessage(0, 0, 0, FIPAMessage.Performative.CFP, query=None)
        msg_bytes = FIPASerializer().encode(msg)
        envelope = Envelope(to="mailbox2", sender="mailbox1", protocol_id=FIPAMessage.protocol_id, message=msg_bytes)
        mailbox1.send(envelope)

        msg = FIPAMessage(0, 0, 0, FIPAMessage.Performative.PROPOSE, proposal=[])
        msg_bytes = FIPASerializer().encode(msg)
        envelope = Envelope(to="mailbox2", sender="mailbox1", protocol_id=FIPAMessage.protocol_id, message=msg_bytes)
        mailbox1.send(envelope)

        msg = FIPAMessage(0, 0, 0, FIPAMessage.Performative.ACCEPT)
        msg_bytes = FIPASerializer().encode(msg)
        envelope = Envelope(to="mailbox2", sender="mailbox1", protocol_id=FIPAMessage.protocol_id, message=msg_bytes)
        mailbox1.send(envelope)

        msg = FIPAMessage(0, 0, 0, FIPAMessage.Performative.DECLINE)
        msg_bytes = FIPASerializer().encode(msg)
        envelope = Envelope(to="mailbox2", sender="mailbox1", protocol_id=FIPAMessage.protocol_id, message=msg_bytes)
        mailbox1.send(envelope)

        time.sleep(5.0)

        envelope = mailbox2.inbox.get(block=True, timeout=1.0)
        msg = DefaultSerializer().decode(envelope.message)
        assert envelope.protocol_id == "default"
        assert msg.get("content") == b"hello"
        envelope = mailbox2.inbox.get(block=True, timeout=1.0)
        msg = FIPASerializer().decode(envelope.message)
        assert envelope.protocol_id == "fipa"
        assert msg.get("performative") == FIPAMessage.Performative.CFP
        envelope = mailbox2.inbox.get(block=True, timeout=1.0)
        msg = FIPASerializer().decode(envelope.message)
        assert envelope.protocol_id == "fipa"
        assert msg.get("performative") == FIPAMessage.Performative.PROPOSE
        envelope = mailbox2.inbox.get(block=True, timeout=1.0)
        msg = FIPASerializer().decode(envelope.message)
        assert envelope.protocol_id == "fipa"
        assert msg.get("performative") == FIPAMessage.Performative.ACCEPT
        envelope = mailbox2.inbox.get(block=True, timeout=1.0)
        msg = FIPASerializer().decode(envelope.message)
        assert envelope.protocol_id == "fipa"
        assert msg.get("performative") == FIPAMessage.Performative.DECLINE

        mailbox1.disconnect()
        mailbox2.disconnect()

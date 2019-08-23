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

from aea.channel.oef import OEFMailBox
from aea.crypto.base import Crypto
from aea.mail.base import Envelope
from aea.protocols.default.message import DefaultMessage
from aea.protocols.fipa.message import FIPAMessage
from aea.protocols.default.serialization import DefaultSerializer
from aea.protocols.fipa.serialization import FIPASerializer


def test_example(network_node):
    """Test the mailbox."""

    crypto1 = Crypto()
    crypto2 = Crypto()

    mailbox1 = OEFMailBox(crypto1.public_key, "127.0.0.1", 10000)
    mailbox2 = OEFMailBox(crypto2.public_key, "127.0.0.1", 10000)

    mailbox1.connect()
    mailbox2.connect()

    msg = DefaultMessage(type=DefaultMessage.Type.BYTES, content=b"hello")
    msg_bytes = DefaultSerializer().encode(msg)
    mailbox1.outbox.put(Envelope(to=crypto2.public_key, sender=crypto1.public_key, protocol_id=DefaultMessage.protocol_id, message=msg_bytes))

    msg = FIPAMessage(message_id=0, dialogue_id=0, target=0, performative=FIPAMessage.Performative.CFP, query=None)
    msg_bytes = FIPASerializer().encode(msg)
    mailbox1.outbox.put(Envelope(to=crypto2.public_key, sender=crypto1.public_key, protocol_id=FIPAMessage.protocol_id, message=msg_bytes))

    msg = FIPAMessage(message_id=0, dialogue_id=0, target=0, performative=FIPAMessage.Performative.PROPOSE, proposal=[])
    msg_bytes = FIPASerializer().encode(msg)
    mailbox1.outbox.put(Envelope(to=crypto2.public_key, sender=crypto1.public_key, protocol_id=FIPAMessage.protocol_id, message=msg_bytes))

    msg = FIPAMessage(message_id=0, dialogue_id=0, target=0, performative=FIPAMessage.Performative.ACCEPT)
    msg_bytes = FIPASerializer().encode(msg)
    mailbox1.outbox.put(Envelope(to=crypto2.public_key, sender=crypto1.public_key, protocol_id=FIPAMessage.protocol_id, message=msg_bytes))

    msg = FIPAMessage(message_id=0, dialogue_id=0, target=0, performative=FIPAMessage.Performative.DECLINE)
    msg_bytes = FIPASerializer().encode(msg)
    mailbox1.outbox.put(Envelope(to=crypto2.public_key, sender=crypto1.public_key, protocol_id=FIPAMessage.protocol_id, message=msg_bytes))

    time.sleep(5.0)

    envelope = mailbox2.inbox.get(block=True, timeout=2.0)
    msg = DefaultSerializer().decode(envelope.message)
    assert msg.get("content") == b"hello"
    envelope = mailbox2.inbox.get(block=True, timeout=2.0)
    msg = FIPASerializer().decode(envelope.message)
    assert envelope.protocol_id == "fipa"
    assert msg.get("performative") == FIPAMessage.Performative.CFP
    envelope = mailbox2.inbox.get(block=True, timeout=2.0)
    msg = FIPASerializer().decode(envelope.message)
    assert envelope.protocol_id == "fipa"
    assert msg.get("performative") == FIPAMessage.Performative.PROPOSE
    envelope = mailbox2.inbox.get(block=True, timeout=2.0)
    msg = FIPASerializer().decode(envelope.message)
    assert envelope.protocol_id == "fipa"
    assert msg.get("performative") == FIPAMessage.Performative.ACCEPT
    envelope = mailbox2.inbox.get(block=True, timeout=2.0)
    msg = FIPASerializer().decode(envelope.message)
    assert envelope.protocol_id == "fipa"
    assert msg.get("performative") == FIPAMessage.Performative.DECLINE

    mailbox1.disconnect()
    mailbox2.disconnect()

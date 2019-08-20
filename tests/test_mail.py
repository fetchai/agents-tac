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

from tac.aea.crypto.base import Crypto

from tac.aea.mail.messages import FIPAMessage, ByteMessage  # OEFMessage
from tac.aea.mail.oef import OEFNetworkMailBox
from tac.aea.mail.protocol import Envelope


def test_example(network_node):
    """Test the mailbox."""
    crypto1 = Crypto()
    crypto2 = Crypto()

    pbk1 = crypto1.public_key
    pbk2 = crypto2.public_key

    mailbox1 = OEFNetworkMailBox(crypto1, "127.0.0.1", 10000)
    mailbox2 = OEFNetworkMailBox(crypto2, "127.0.0.1", 10000)

    mailbox1.connect()
    mailbox2.connect()

    msg = ByteMessage(message_id=0, dialogue_id=0, content=b"hello")
    mailbox1.outbox.put(Envelope(to=pbk1, sender=pbk2, protocol_id=ByteMessage.protocol_id, message=msg))
    msg = FIPAMessage(0, 0, 0, FIPAMessage.Performative.CFP, query=None)
    mailbox1.outbox.put(Envelope(to=pbk1, sender=pbk2, protocol_id=FIPAMessage.protocol_id, message=msg))
    msg = FIPAMessage(0, 0, 0, FIPAMessage.Performative.PROPOSE, proposal=[])
    mailbox1.outbox.put(Envelope(to=pbk1, sender=pbk2, protocol_id=FIPAMessage.protocol_id, message=msg))
    msg = FIPAMessage(0, 0, 0, FIPAMessage.Performative.ACCEPT)
    mailbox1.outbox.put(Envelope(to=pbk1, sender=pbk2, protocol_id=FIPAMessage.protocol_id, message=msg))
    msg = FIPAMessage(0, 0, 0, FIPAMessage.Performative.DECLINE)
    mailbox1.outbox.put(Envelope(to=pbk1, sender=pbk2, protocol_id=FIPAMessage.protocol_id, message=msg))

    time.sleep(10.0)

    msg = mailbox2.inbox.get(block=True, timeout=2.0)
    assert msg.message.get("content") == b"hello"
    msg = mailbox2.inbox.get(block=True, timeout=2.0)
    assert msg.protocol_id == "fipa"
    assert msg.message.get("performative") == FIPAMessage.Performative.CFP
    msg = mailbox2.inbox.get(block=True, timeout=2.0)
    assert msg.protocol_id == "fipa"
    assert msg.message.get("performative") == FIPAMessage.Performative.PROPOSE
    msg = mailbox2.inbox.get(block=True, timeout=2.0)
    assert msg.protocol_id == "fipa"
    assert msg.message.get("performative") == FIPAMessage.Performative.ACCEPT
    msg = mailbox2.inbox.get(block=True, timeout=2.0)
    assert msg.protocol_id == "fipa"
    assert msg.message.get("performative") == FIPAMessage.Performative.DECLINE

    mailbox1.disconnect()
    mailbox2.disconnect()

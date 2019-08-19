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

"""Mail module abstract base classes."""

import logging
from abc import abstractmethod
from queue import Queue
from typing import Optional

from tac.aea.mail.messages import Address, ProtocolId, Message
from tac.aea.mail.protocol import Envelope


logger = logging.getLogger(__name__)


class InBox(object):
    """A queue from where you can only consume messages."""

    def __init__(self, queue: Queue):
        """
        Initialize the inbox.

        :param queue: the queue.
        """
        super().__init__()
        self._queue = queue

    def empty(self) -> bool:
        """
        Check for a message on the in queue.

        :return: boolean indicating whether there is a message or not
        """
        return self._queue.empty()

    def get(self, block: bool = True, timeout: Optional[float] = None) -> Optional[Envelope]:
        """
        Check for a message on the in queue.

        :param block: if true makes it blocking.
        :param timeout: times out the block after timeout seconds.

        :return: the message object.
        """
        logger.debug("Checks for message from the in queue...")
        msg = self._queue.get(block=block, timeout=timeout)
        logger.debug("Incoming message type: type={}".format(type(msg)))
        return msg

    def get_nowait(self) -> Optional[Envelope]:
        """
        Check for a message on the in queue and wait for no time.

        :return: the message object
        """
        item = self._queue.get_nowait()
        return item


class OutBox(object):
    """A queue from where you can only enqueue messages."""

    def __init__(self, queue: Queue) -> None:
        """
        Initialize the outbox.

        :param queue: the queue.
        """
        super().__init__()
        self._queue = queue

    def empty(self) -> bool:
        """
        Check for a message on the out queue.

        :return: boolean indicating whether there is a message or not
        """
        return self._queue.empty()

    def put(self, item: Envelope) -> None:
        """
        Put an item into the queue.

        :param item: the message.
        :return: None
        """
        logger.debug("Put a message in the queue...")
        self._queue.put(item)

    def put_message(self, to: Optional[Address] = None, sender: Optional[Address] = None,
                    protocol_id: Optional[ProtocolId] = None, message: Optional[Message] = None) -> None:
        """
        Put a message in the outbox.

        :param to: the recipient of the message.
        :param sender: the sender of the message.
        :param protocol_id: the protocol id.
        :param message: the content of the message.
        :return: None
        """
        envelope = Envelope(to=to, sender=sender, protocol_id=protocol_id, message=message)
        self._queue.put(envelope)


class Connection:
    """Abstract definition of a connection."""

    def __init__(self):
        """Initialize the connection."""
        self.in_queue = Queue()
        self.out_queue = Queue()

    @abstractmethod
    def connect(self):
        """Set up the connection."""

    @abstractmethod
    def disconnect(self):
        """Tear down the connection."""

    @property
    @abstractmethod
    def is_established(self) -> bool:
        """Check if the connection is established."""

    @abstractmethod
    def send(self, msg: Envelope):
        """Send a message."""


class MailBox(object):
    """Abstract definition of a mailbox."""

    def __init__(self, connection: Connection):
        """Initialize the mailbox."""
        self._connection = connection

        self.inbox = InBox(self._connection.in_queue)
        self.outbox = OutBox(self._connection.out_queue)

    @property
    def is_connected(self) -> bool:
        """Check whether the mailbox is processing messages."""
        return self._connection.is_established

    def connect(self) -> None:
        """Connect."""
        self._connection.connect()

    def disconnect(self) -> None:
        """Disconnect."""
        self._connection.disconnect()

    def send(self, out: Envelope) -> None:
        """Send."""
        self.outbox.put(out)

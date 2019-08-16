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

"""
Mail module v2.
"""

import logging
from abc import abstractmethod, ABC
from queue import Queue
from typing import Optional

from tac.agents.v1.mail.messages import Message

logger = logging.getLogger(__name__)


class InBox(object):
    """A queue from where you can only consume messages."""

    def __init__(self, queue: Queue):
        """Initialize the inbox."""
        super().__init__()
        self._queue = queue

    def empty(self) -> bool:
        """
        Check for a message on the in queue.

        :return: boolean indicating whether there is a message or not
        """
        return self._queue.empty()

    def get(self, block: bool = True, timeout: Optional[float] = None) -> Optional[Message]:
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

    def get_nowait(self):
        """
        Check for a message on the in queue and wait for no time.

        :return: the message object
        """
        item = self._queue.get_nowait()
        return item


class OutBox(object):
    """A queue from where you can only enqueue messages."""

    def __init__(self, queue: Queue) -> None:
        """Initialize the outbox."""
        super().__init__()
        self._queue = queue

    def empty(self) -> bool:
        """
        Check for a message on the out queue.

        :return: boolean indicating whether there is a message or not
        """
        return self._queue.empty()

    def put(self, item: Message) -> None:
        """Put an item into the queue."""
        logger.debug("Put a message in the queue...")
        self._queue.put(item)


class Connection:

    def __init__(self):
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
    def send(self, msg: Message):
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

    def connect(self):
        self._connection.connect()

    def disconnect(self):
        self._connection.disconnect()

    def send(self, out: Message):
        self.outbox.put(out)


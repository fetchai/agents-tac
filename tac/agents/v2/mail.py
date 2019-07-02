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
import logging
import asyncio
from queue import Queue, Empty
from threading import Thread
from typing import List, Optional, Any, Union

from oef.agents import OEFAgent
from oef.messages import PROPOSE_TYPES, CFP_TYPES, CFP, Decline, Propose, Accept, Message as ByteMessage, \
    SearchResult, OEFErrorOperation, OEFErrorMessage, DialogueErrorMessage
from oef.query import Query
from oef.schema import Description
from oef.utils import Context

logger = logging.getLogger(__name__)

Action = Any
OEFMessage = Union[SearchResult, OEFErrorMessage, DialogueErrorMessage]
ControllerMessage = ByteMessage
AgentMessage = Union[ByteMessage, CFP, Propose, Accept, Decline]
Message = Union[OEFMessage, ControllerMessage, AgentMessage]


class MailBox(OEFAgent):
    """
    The MailBox enqueues incoming messages, searches and errors from the OEF and sends outgoing messages to the OEF.
    """

    def __init__(self, public_key: str, oef_addr: str, oef_port: int = 10000):
        super().__init__(public_key, oef_addr, oef_port, loop=asyncio.new_event_loop())
        self.connect()
        self.in_queue = Queue()
        self.out_queue = Queue()
        self._mail_box_thread = None  # type: Optional[Thread]

    def on_message(self, msg_id: int, dialogue_id: int, origin: str, content: bytes) -> None:
        self.in_queue.put(ByteMessage(msg_id, dialogue_id, origin, content, Context()))

    def on_search_result(self, search_id: int, agents: List[str]) -> None:
        self.in_queue.put(SearchResult(search_id, agents))

    def on_oef_error(self, answer_id: int, operation: OEFErrorOperation) -> None:
        self.in_queue.put(OEFErrorMessage(answer_id, operation))

    def on_dialogue_error(self, answer_id: int, dialogue_id: int, origin: str) -> None:
        self.in_queue.put(DialogueErrorMessage(answer_id, dialogue_id, origin))

    def is_running(self) -> bool:
        return self._mail_box_thread is None

    def start(self) -> None:
        """
        Starts the mailbox.

        :return: None
        """
        self._mail_box_thread = Thread(target=super().run)
        self._mail_box_thread.start()

    def stop(self) -> None:
        """
        Stops the mailbox.

        :return: None
        """
        self._loop.call_soon_threadsafe(super().stop)
        if self._mail_box_thread is not None:
            self._mail_box_thread.join()
            self._mail_box_thread = None


class InBox(object):
    """
    Temporarily stores messages for the agent.
    """

    def __init__(self, mail_box: MailBox, timeout: float = 1.0):
        self._mail_box = mail_box
        self._timeout = timeout

    @property
    def in_queue(self) -> Queue:
        return self._mail_box.in_queue

    @property
    def timeout(self) -> float:
        return self._timeout

    def is_in_queue_empty(self) -> bool:
        """
        Checks for a message on the in queue.

        :return: boolean indicating whether there is a message or not
        """
        result = self.in_queue.empty()
        return result

    def get_wait(self) -> AgentMessage:
        """
        Waits for a message on the in queue and gets it. Blocking.

        :return: the message object
        """
        logger.debug("Waiting for message from the in queue...")
        msg = self.in_queue.get()
        logger.debug("Incoming message type: type={}".format(type(msg)))
        return msg

    def get_some_wait(self, block: bool = True, timeout: Optional[float] = None) -> Optional[AgentMessage]:
        """
        Checks for a message on the in queue for some time and gets it.

        :param block: if true makes it blocking
        :param timeout: times out the block after timeout seconds
        :return: the message object
        """
        logger.debug("Checks for message from the in queue...")
        try:
            msg = self.in_queue.get(block=block, timeout=timeout)
            logger.debug("Incoming message type: type={}".format(type(msg)))
            return msg
        except Empty:
            return None

    def get_no_wait(self) -> Optional[AgentMessage]:
        """
        Checks for a message on the in queue for no time.

        :return: the message object
        """
        result = self.get_some_wait(False)
        return result

class OutBox(object):
    """
    Temporarily stores and sends messages to the OEF and other agents.
    """

    def __init__(self, mail_box: MailBox):
        self._mail_box = mail_box

    @property
    def out_queue(self) -> Queue:
        return self._mail_box.out_queue

    @property
    def mail_box(self) -> MailBox:
        return self._mail_box

    def send_nowait(self) -> None:
        """
        Checks whether the out queue contains a message or search query and sends it in that case. Non-blocking.

        :return: None
        """
        logger.debug("Checking for message or search query on out queue...")
        while not self.out_queue.empty():
            out = self.out_queue.get_nowait()
            if isinstance(out, OutContainer) and out.message is not None:
                logger.debug("Outgoing message type: type={}".format(type(out.message)))
                self.mail_box.send_message(out.message_id, out.dialogue_id, out.destination, out.message)
            elif isinstance(out, OutContainer) and (out.service_description is not None) and (not out.is_unregister):
                logger.debug("Outgoing register service description: message_id={}".format(type(out.service_description), out.message_id))
                self.mail_box.register_service(out.message_id, out.service_description)
            elif isinstance(out, OutContainer) and out.service_description is not None:
                logger.debug("Outgoing unregister service description: message_id={}".format(type(out.service_description), out.message_id))
                self.mail_box.unregister_service(out.message_id, out.service_description)
            elif isinstance(out, OutContainer) and out.query is not None:
                logger.debug("Outgoing query: search_id={}".format(out.search_id))
                self.mail_box.search_services(out.search_id, out.query)
            elif isinstance(out, CFP):
                logger.debug("Outgoing cfp: msg_id={}, dialogue_id={}, origin={}, target={}, query={}".format(out.msg_id, out.dialogue_id, out.destination, out.target, out.query))
                self.mail_box.send_cfp(out.msg_id, out.dialogue_id, out.destination, out.target, out.query)
            elif isinstance(out, Propose):
                logger.debug("Outgoing propose: msg_id={}, dialogue_id={}, origin={}, target={}, propose={}".format(out.msg_id, out.dialogue_id, out.destination, out.target, out.proposals[0].values))
                self.mail_box.send_propose(out.msg_id, out.dialogue_id, out.destination, out.target, out.proposals)
            elif isinstance(out, Accept):
                logger.debug("Outgoing accept: msg_id={}, dialogue_id={}, origin={}, target={}".format(out.msg_id, out.dialogue_id, out.destination, out.target))
                self.mail_box.send_accept(out.msg_id, out.dialogue_id, out.destination, out.target)
            elif isinstance(out, Decline):
                logger.debug("Outgoing decline: msg_id={}, dialogue_id={}, origin={}, target={}".format(out.msg_id, out.dialogue_id, out.destination, out.target))
                self.mail_box.send_decline(out.msg_id, out.dialogue_id, out.destination, out.target)
            elif isinstance(out, ByteMessage):
                logger.debug("Outgoing dialogue error message: msg_id={}, dialogue_id={}, origin={}, message={}".format(out.msg_id, out.dialogue_id, out.destination, out.msg))
                # self.mail_box.send_message(out.msg_id, out.dialogue_id, out.destination, out.target, out.message)
            else:
                logger.debug("Unknown object on out queue... type={}".format(type(out)))


class FIPAMailBox(MailBox):
    """
    The FIPAMailBox enqueues additionally FIPA specific messages.
    """

    def __init__(self, public_key: str, oef_addr: str, oef_port: int = 10000):
        super().__init__(public_key, oef_addr, oef_port)

    def on_cfp(self, msg_id: int, dialogue_id: int, origin: str, target: int, query: CFP_TYPES) -> None:
        self.in_queue.put(CFP(msg_id, dialogue_id, origin, target, query, Context()))

    def on_propose(self, msg_id: int, dialogue_id: int, origin: str, target: int, proposals: PROPOSE_TYPES) -> None:
        self.in_queue.put(Propose(msg_id, dialogue_id, origin, target, proposals, Context()))

    def on_accept(self, msg_id: int, dialogue_id: int, origin: str, target: int) -> None:
        self.in_queue.put(Accept(msg_id, dialogue_id, origin, target, Context()))

    def on_decline(self, msg_id: int, dialogue_id: int, origin: str, target: int) -> None:
        self.in_queue.put(Decline(msg_id, dialogue_id, origin, target, Context()))


class OutContainer:
    """
    The OutContainer is a container to keep a message or search in whilst on the out queue.
    """

    def __init__(self, message: Optional[bytes] = None,
                 message_id: Optional[int] = None,
                 dialogue_id: Optional[int] = None,
                 destination: Optional[str] = None,
                 query: Optional[Query] = None,
                 search_id: Optional[int] = None,
                 service_description: Optional[Description] = None,
                 is_unregister: Optional[bool] = False):
        self.message = message
        self.message_id = message_id
        self.dialogue_id = dialogue_id
        self.destination = destination
        self.query = query
        self.search_id = search_id
        self.service_description = service_description
        self.is_unregister = is_unregister

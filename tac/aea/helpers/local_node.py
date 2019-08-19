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

"""Naive implementation of the OEF Node features."""

import asyncio
import logging
import queue
import threading
from asyncio import AbstractEventLoop, Queue
from collections import defaultdict
from threading import Thread
from typing import Dict, List, Tuple, Optional

from oef import agent_pb2, uri
from oef.core import OEFProxy
from oef.messages import BaseMessage, AgentMessage, OEFErrorOperation, OEFErrorMessage, SearchResult, \
    DialogueErrorMessage, PROPOSE_TYPES, Message, CFP, Propose, Accept, Decline, CFP_TYPES
from oef.proxy import OEFConnectionError
from oef.query import Query
from oef.schema import Description

logger = logging.getLogger(__name__)


class LocalNode:
    """A light-weight local implementation of a OEF Node."""

    def __init__(self):
        """Initialize a local (i.e. non-networked) implementation of an OEF Node."""
        self.agents = dict()  # type: Dict[str, Description]
        self.services = defaultdict(lambda: [])  # type: Dict[str, List[Description]]
        self._lock = threading.Lock()

        self.loop = asyncio.new_event_loop()
        self._task = None  # type: Optional[asyncio.Task]
        self._stopped = True  # type: bool
        self._thread = None  # type: Optional[Thread]

        self._read_queue = Queue(loop=self.loop)  # type: Queue
        self._queues = {}  # type: Dict[str, asyncio.Queue]
        self._loops = {}  # type: Dict[str, AbstractEventLoop]

    def __enter__(self):
        """Start the OEF Node."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop the OEF Node."""
        self.stop()

    def connect(self, public_key: str, loop: AbstractEventLoop) -> Optional[Tuple[Queue, Queue]]:
        """
        Connect a public key to the node.

        :param public_key: the public key of the agent.
        :return: an asynchronous queue, that constitutes the communication channel.
        """
        if public_key in self._queues:
            return None

        q = Queue(loop=loop)
        self._queues[public_key] = q
        self._loops[public_key] = loop
        return self._read_queue, q

    async def _process_messages(self) -> None:
        """
        Process the incoming messages.

        :return: None
        """
        while not self._stopped:
            try:
                data = await self._read_queue.get()  # type: Tuple[str, BaseMessage]
            except asyncio.CancelledError:
                logger.debug("Local Node: loop cancelled.")
                break
            public_key, msg = data
            assert isinstance(msg, AgentMessage)
            logger.debug("Processing message from {}: {}".format(public_key, msg))
            self._send_agent_message(public_key, msg)

    def run(self) -> None:
        """
        Run the node, i.e. start processing the messages.

        :return: None
        """
        self._stopped = False
        self._task = asyncio.ensure_future(self._process_messages(), loop=self.loop)
        self.loop.run_until_complete(self._task)

    def start(self):
        """Start the node in its own thread."""
        self._thread = Thread(target=self.run)
        self._thread.start()

    def stop(self) -> None:
        """
        Stop the execution of the node.

        :return: None
        """
        self._stopped = True

        if self._task and not self._task.cancelled():
            self.loop.call_soon_threadsafe(self._task.cancel)

        if self._thread:
            self._thread.join()

    def register_agent(self, public_key: str, agent_description: Description) -> None:
        """
        Register an agent in the agent directory of the node.

        :param public_key: the public key of the agent to be registered.
        :param agent_description: the description of the agent to be registered.
        :return: None
        """
        with self._lock:
            self.agents[public_key] = agent_description

    def register_service(self, public_key: str, service_description: Description):
        """
        Register a service agent in the service directory of the node.

        :param public_key: the public key of the service agent to be registered.
        :param service_description: the description of the service agent to be registered.
        :return: None
        """
        with self._lock:
            self.services[public_key].append(service_description)

    def register_service_wide(self, public_key: str, service_description: Description):
        """Register service wide."""
        raise NotImplementedError

    def unregister_agent(self, public_key: str, msg_id: int) -> None:
        """
        Unregister an agent.

        :param public_key: the public key of the agent to be unregistered.
        :param msg_id: the message id of the request.
        :return: None
        """
        with self._lock:
            if public_key not in self.agents:
                msg = OEFErrorMessage(msg_id, OEFErrorOperation.UNREGISTER_DESCRIPTION)
                self._send(public_key, msg.to_pb())
            else:
                self.agents.pop(public_key)

    def unregister_service(self, public_key: str, msg_id: int, service_description: Description) -> None:
        """
        Unregister a service agent.

        :param public_key: the public key of the service agent to be unregistered.
        :param msg_id: the message id of the request.
        :param service_description: the description of the service agent to be unregistered.
        :return: None
        """
        with self._lock:
            if public_key not in self.services:
                msg = OEFErrorMessage(msg_id, OEFErrorOperation.UNREGISTER_SERVICE)
                self._send(public_key, msg.to_pb())
            else:
                self.services[public_key].remove(service_description)
                if len(self.services[public_key]) == 0:
                    self.services.pop(public_key)

    def search_agents(self, public_key: str, search_id: int, query: Query) -> None:
        """
        Search the agents in the local Agent Directory, and send back the result.

        The provided query will be checked with every instance of the Agent Directory.

        :param public_key: the source of the search request.
        :param search_id: the search identifier associated with the search request.
        :param query: the query that constitutes the search.
        :return: None
        """
        result = []
        for agent_public_key, description in self.agents.items():
            if query.check(description):
                result.append(agent_public_key)

        msg = SearchResult(search_id, sorted(set(result)))
        self._send(public_key, msg.to_pb())

    def search_services(self, public_key: str, search_id: int, query: Query) -> None:
        """
        Search the agents in the local Service Directory, and send back the result.

        The provided query will be checked with every instance of the Agent Directory.

        :param public_key: the source of the search request.
        :param search_id: the search identifier associated with the search request.
        :param query: the query that constitutes the search.
        :return: None
        """
        result = []
        for agent_public_key, descriptions in self.services.items():
            for description in descriptions:
                if query.check(description):
                    result.append(agent_public_key)

        msg = SearchResult(search_id, sorted(set(result)))
        self._send(public_key, msg.to_pb())

    def _send_agent_message(self, origin: str, msg: AgentMessage) -> None:
        """
        Send an :class:`~oef.messages.AgentMessage`.

        :param origin: the public key of the sender agent.
        :param msg: the message.
        :return: None
        """
        e = msg.to_pb()
        destination = e.send_message.destination

        if destination not in self._queues:
            msg = DialogueErrorMessage(msg.msg_id, e.send_message.dialogue_id, destination)
            self._send(origin, msg.to_pb())
            return

        new_msg = agent_pb2.Server.AgentMessage()
        new_msg.answer_id = msg.msg_id
        new_msg.content.origin = origin
        new_msg.content.dialogue_id = e.send_message.dialogue_id

        payload = e.send_message.WhichOneof("payload")
        if payload == "content":
            new_msg.content.content = e.send_message.content
        elif payload == "fipa":
            new_msg.content.fipa.CopyFrom(e.send_message.fipa)

        self._send(destination, new_msg)

    def _send(self, public_key: str, msg):
        loop = self._loops[public_key]
        loop.call_soon_threadsafe(self._queues[public_key].put_nowait, msg.SerializeToString())


class OEFLocalProxy(OEFProxy):
    """
    Proxy to the functionality of the OEF.

    It allows the interaction between agents, but not the search functionality.
    It is useful for local testing.
    """

    def __init__(self, public_key: str, local_node: LocalNode, loop: asyncio.AbstractEventLoop = None):
        """
        Initialize a OEF proxy for a local OEF Node (that is, :class:`~oef.proxy.OEFLocalProxy.LocalNode`.

        :param public_key: the public key used in the protocols.
        :param local_node: the Local OEF Node object. This reference must be the same across the agents of interest.
        :param loop: the event loop.
        """
        super().__init__(public_key, loop)
        self.local_node = local_node
        self._connection = None  # type: Optional[Tuple[queue.Queue, queue.Queue]]
        self._read_queue = None  # type: Optional[Queue]
        self._write_queue = None  # type: Optional[Queue]

    def register_agent(self, msg_id: int, agent_description: Description) -> None:
        """Register an agent."""
        self.local_node.register_agent(self.public_key, agent_description)

    def register_service(self, msg_id: int, service_description: Description, service_id: str = "") -> None:
        """Register a service."""
        self.local_node.register_service(self.public_key, service_description)

    def search_agents(self, search_id: int, query: Query) -> None:
        """Search agents."""
        self.local_node.search_agents(self.public_key, search_id, query)

    def search_services(self, search_id: int, query: Query) -> None:
        """Search services."""
        self.local_node.search_services(self.public_key, search_id, query)

    def search_services_wide(self, msg_id: int, query: Query) -> None:
        """Search wide."""
        raise NotImplementedError

    def unregister_agent(self, msg_id: int) -> None:
        """Unregister an agent."""
        self.local_node.unregister_agent(self.public_key, msg_id)

    def unregister_service(self, msg_id: int, service_description: Description, service_id: str = "") -> None:
        """Unregister a service."""
        self.local_node.unregister_service(self.public_key, msg_id, service_description)

    def send_message(self, msg_id: int, dialogue_id: int, destination: str, msg: bytes, context=uri.Context()):
        """Send a simple message."""
        msg = Message(msg_id, dialogue_id, destination, msg, context)
        self._send(msg)

    def send_cfp(self, msg_id: int, dialogue_id: int, destination: str, target: int, query: CFP_TYPES, context=uri.Context()) -> None:
        """Send a CFP."""
        msg = CFP(msg_id, dialogue_id, destination, target, query, context)
        self._send(msg)

    def send_propose(self, msg_id: int, dialogue_id: int, destination: str, target: int, proposals: PROPOSE_TYPES, context=uri.Context()) -> None:
        """Send a propose."""
        msg = Propose(msg_id, dialogue_id, destination, target, proposals, context)
        self._send(msg)

    def send_accept(self, msg_id: int, dialogue_id: int, destination: str, target: int, context=uri.Context()) -> None:
        """Send an accept."""
        msg = Accept(msg_id, dialogue_id, destination, target, context)
        self._send(msg)

    def send_decline(self, msg_id: int, dialogue_id: int, destination: str, target: int, context=uri.Context()) -> None:
        """Send a decline."""
        msg = Decline(msg_id, dialogue_id, destination, target, context)
        self._send(msg)

    async def connect(self) -> bool:
        """Connect the proxy."""
        if self._connection is not None:
            return True

        self._connection = self.local_node.connect(self.public_key, self._loop)
        if self._connection is None:
            return False
        self._write_queue, self._read_queue = self._connection
        return True

    async def _receive(self) -> bytes:
        """Receive a message."""
        if not self.is_connected():
            raise OEFConnectionError("Connection not established yet. Please use 'connect()'.")
        data = await self._read_queue.get()
        return data

    def _send(self, msg: BaseMessage) -> None:
        """Send a message."""
        if not self.is_connected():
            raise OEFConnectionError("Connection not established yet. Please use 'connect()'.")
        self.local_node.loop.call_soon_threadsafe(self._write_queue.put_nowait, (self.public_key, msg))

    async def stop(self):
        """Tear down the connection."""
        self._connection = None
        self._read_queue = None
        self._write_queue = None

    def is_connected(self) -> bool:
        """Return True if the proxy is connected, False otherwise."""
        return self._connection is not None

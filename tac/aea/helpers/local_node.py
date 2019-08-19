import asyncio
import logging
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

Envelope = None

logger = logging.getLogger(__name__)


class LocalNode:
    """A light-weight local implementation of a OEF Node."""

    def __init__(self, loop=None):
        """
        Initialize a local (i.e. non-networked) implementation of an OEF Node
        """
        self.agents = dict()  # type: Dict[str, Description]
        self.services = defaultdict(lambda: [])  # type: Dict[str, List[Description]]
        self.loop = asyncio.get_event_loop() if loop is None else loop
        self._lock = asyncio.Lock()
        self._thread = Thread(target=self.run)

        self._read_queue = asyncio.Queue()  # type: asyncio.Queue
        self._queues = {}  # type: Dict[str, asyncio.Queue]

    def __enter__(self):
        self._thread.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def connect(self, public_key: str) -> Optional[Tuple[asyncio.Queue, asyncio.Queue]]:
        """
        Connect a public key to the node.

        :param public_key: the public key of the agent.
        :return: an asynchronous queue, that constitutes the communication channel.
        """
        if public_key in self._queues:
            return None

        queue = asyncio.Queue()
        self._queues[public_key] = queue
        return self._read_queue, queue

    def _process_messages(self) -> None:
        """
        Main event loop to process the incoming messages.

        :return: ``None``
        """
        while True:
            try:
                data = await self._read_queue.get()  # type: Tuple[str, BaseMessage]
            except asyncio.CancelledError:
                logger.debug("Local Node: loop cancelled.")
                break

            public_key, msg = data
            assert isinstance(msg, AgentMessage)
            self._send_agent_message(public_key, msg)

    def run(self) -> None:
        """
        Run the node, i.e. start processing the messages.

        :return: ``None``
        """
        self._process_messages()

    def stop(self) -> None:
        """
        Stop the execution of the node.

        :return: ``None``
        """
        pass

    def register_agent(self, public_key: str, agent_description: Description) -> None:
        """
        Register an agent in the agent directory of the node.

        :param public_key: the public key of the agent to be registered.
        :param agent_description: the description of the agent to be registered.
        :return: ``None``
        """
        self.loop.run_until_complete(self._lock.acquire())
        self.agents[public_key] = agent_description
        self._lock.release()

    def register_service(self, public_key: str, service_description: Description):
        """
        Register a service agent in the service directory of the node.

        :param public_key: the public key of the service agent to be registered.
        :param service_description: the description of the service agent to be registered.
        :return: ``None``
        """
        self.loop.run_until_complete(self._lock.acquire())
        self.services[public_key].append(service_description)
        self._lock.release()

    def register_service_wide(self, public_key: str, service_description: Description):
        self.register_service(public_key, service_description)

    def unregister_agent(self, public_key: str, msg_id: int) -> None:
        """
        Unregister an agent.

        :param public_key: the public key of the agent to be unregistered.
        :param msg_id: the message id of the request.
        :return: ``None``
        """
        self.loop.run_until_complete(self._lock.acquire())
        if public_key not in self.agents:
            msg = OEFErrorMessage(msg_id, OEFErrorOperation.UNREGISTER_DESCRIPTION)
            self._send(public_key, msg.to_pb())
        else:
            self.agents.pop(public_key)
        self._lock.release()

    def unregister_service(self, public_key: str, msg_id: int, service_description: Description) -> None:
        """
        Unregister a service agent.

        :param public_key: the public key of the service agent to be unregistered.
        :param msg_id: the message id of the request.
        :param service_description: the description of the service agent to be unregistered.
        :return: ``None``
        """
        self.loop.run_until_complete(self._lock.acquire())

        if public_key not in self.services:
            msg = OEFErrorMessage(msg_id, OEFErrorOperation.UNREGISTER_SERVICE)
            self._send(public_key, msg.to_pb())
        else:
            self.services[public_key].remove(service_description)
            if len(self.services[public_key]) == 0:
                self.services.pop(public_key)
        self._lock.release()

    def search_agents(self, public_key: str, search_id: int, query: Query) -> None:
        """
        Search the agents in the local Agent Directory, and send back the result.
        The provided query will be checked with every instance of the Agent Directory.

        :param public_key: the source of the search request.
        :param search_id: the search identifier associated with the search request.
        :param query: the query that constitutes the search.
        :return: ``None``
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
        :return: ``None``
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
        :return: ``None``
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

        self._queues[destination].put_nowait(new_msg.SerializeToString())

    def _send(self, public_key: str, msg):
        self._queues[public_key].put_nowait(msg.SerializeToString())


class OEFLocalProxy(OEFProxy):
    """
    Proxy to the functionality of the OEF.
    It allows the interaction between agents, but not the search functionality.
    It is useful for local testing.
    """

    def __init__(self, public_key: str, local_node: LocalNode, loop: asyncio.AbstractEventLoop = None):
        """
        Initialize a OEF proxy for a local OEF Node (that is, :class:`~oef.proxy.OEFLocalProxy.LocalNode`

        :param public_key: the public key used in the protocols.
        :param local_node: the Local OEF Node object. This reference must be the same across the agents of interest.
        :param loop: the event loop.
        """

        super().__init__(public_key, loop)
        self.local_node = local_node
        self._connection = None
        self._read_queue = None
        self._write_queue = None

    def register_agent(self, msg_id: int, agent_description: Description) -> None:
        self.local_node.register_agent(self.public_key, agent_description)

    def register_service(self, msg_id: int, service_description: Description, service_id: str = "") -> None:
        self.local_node.register_service(self.public_key, service_description)

    def search_agents(self, search_id: int, query: Query) -> None:
        self.local_node.search_agents(self.public_key, search_id, query)

    def search_services(self, search_id: int, query: Query) -> None:
        self.local_node.search_services(self.public_key, search_id, query)

    def search_services_wide(self, msg_id: int, query: Query) -> None:
        raise NotImplementedError

    def unregister_agent(self, msg_id: int) -> None:
        self.local_node.unregister_agent(self.public_key, msg_id)

    def unregister_service(self, msg_id: int, service_description: Description, service_id: str = "") -> None:
        self.local_node.unregister_service(self.public_key, msg_id, service_description)

    def send_message(self, msg_id: int, dialogue_id: int, destination: str, msg: bytes):
        msg = Message(msg_id, dialogue_id, destination, msg, uri.Context())
        self._send(msg)

    def send_cfp(self, msg_id: int, dialogue_id: int, destination: str, target: int, query: CFP_TYPES, context=uri.Context()) -> None:
        msg = CFP(msg_id, dialogue_id, destination, target, query, context)
        self._send(msg)

    def send_propose(self, msg_id: int, dialogue_id: int, destination: str, target: int, proposals: PROPOSE_TYPES, context=uri.Context()) -> None:
        msg = Propose(msg_id, dialogue_id, destination, target, proposals, context)
        self._send(msg)

    def send_accept(self, msg_id: int, dialogue_id: int, destination: str, target: int, context=uri.Context()) -> None:
        msg = Accept(msg_id, dialogue_id, destination, target, context)
        self._send(msg)

    def send_decline(self, msg_id: int, dialogue_id: int, destination: str, target: int, context=uri.Context()) -> None:
        msg = Decline(msg_id, dialogue_id, destination, target, context)
        self._send(msg)

    async def connect(self) -> bool:
        if self._connection is not None:
            return True

        self._connection = self.local_node.connect(self.public_key)
        if self._connection is None:
            return False
        self._write_queue, self._read_queue = self._connection
        return True

    async def _receive(self) -> bytes:
        if not self.is_connected():
            raise OEFConnectionError("Connection not established yet. Please use 'connect()'.")
        data = await self._read_queue.get()
        return data

    def _send(self, msg: BaseMessage) -> None:
        if not self.is_connected():
            raise OEFConnectionError("Connection not established yet. Please use 'connect()'.")
        self._write_queue.put_nowait((self.public_key, msg))

    async def stop(self):
        self._connection = None
        self._read_queue = None
        self._write_queue = None

    def is_connected(self) -> bool:
        return self._connection is not None
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

"""Extension to the OEF Python SDK."""
import asyncio
import datetime
import logging
from queue import Empty, Queue
from threading import Thread
from typing import List, Dict

from oef.agents import Agent
from oef.core import OEFProxy
from oef.messages import OEFErrorOperation, CFP_TYPES, PROPOSE_TYPES
from oef.proxy import OEFNetworkProxy

from tac.agents.v1.mail.base import Connection, MailBox
from tac.agents.v1.mail.messages import OEFMessage, FIPAMessage, Message, ByteMessage

logger = logging.getLogger(__name__)


class MailStats(object):
    """The MailStats class tracks statistics on messages processed by MailBox."""

    def __init__(self) -> None:
        """
        Instantiate mail stats.

        :return: None
        """
        self._search_count = 0
        self._search_start_time = {}  # type: Dict[int, datetime.datetime]
        self._search_timedelta = {}  # type: Dict[int, float]
        self._search_result_counts = {}  # type: Dict[int, int]

    @property
    def search_count(self) -> int:
        """Get the search count."""
        return self._search_count

    def search_start(self, search_id: int) -> None:
        """
        Add a search id and start time.

        :param search_id: the search id

        :return: None
        """
        assert search_id not in self._search_start_time
        self._search_count += 1
        self._search_start_time[search_id] = datetime.datetime.now()

    def search_end(self, search_id: int, nb_search_results: int) -> None:
        """
        Add end time for a search id.

        :param search_id: the search id
        :param nb_search_results: the number of agents returned in the search result

        :return: None
        """
        assert search_id in self._search_start_time
        assert search_id not in self._search_timedelta
        self._search_timedelta[search_id] = (datetime.datetime.now() - self._search_start_time[search_id]).total_seconds() * 1000
        self._search_result_counts[search_id] = nb_search_results


class OEFChannel(Agent):
    """The OEFChannel connects the OEF Agent with the connection."""

    def __init__(self, oef_proxy: OEFProxy, in_queue: Queue):
        """
        Initialize.

        :param oef_proxy: the OEFProxy.
        :param in_queue: the in queue.
        """
        super().__init__(oef_proxy)
        self.in_queue = in_queue
        self.mail_stats = MailStats()

    def is_connected(self) -> bool:
        """Get connected status."""
        return self._oef_proxy.is_connected()

    def is_active(self) -> bool:
        """Get active status."""
        return self._oef_proxy._active_loop

    def on_message(self, msg_id: int, dialogue_id: int, origin: str, content: bytes) -> None:
        """
        On message event handler.

        :param msg_id: the message id.
        :param dialogue_id: the dialogue id.
        :param origin: the public key of the sender.
        :param content: the bytes content.
        :return: None
        """
        msg = ByteMessage(to=self.public_key,
                          sender=origin,
                          message_id=msg_id,
                          dialogue_id=dialogue_id,
                          content=content)
        self.in_queue.put(msg)

    def on_cfp(self, msg_id: int, dialogue_id: int, origin: str, target: int, query: CFP_TYPES) -> None:
        """
        On cfp event handler.

        :param msg_id: the message id.
        :param dialogue_id: the dialogue id.
        :param origin: the public key of the sender.
        :param target: the message target.
        :param query: the query.
        :return: None
        """
        msg = FIPAMessage(to=self.public_key,
                          sender=origin,
                          message_id=msg_id,
                          dialogue_id=dialogue_id,
                          target=target,
                          performative=FIPAMessage.Performative.CFP,
                          query=query)
        self.in_queue.put(msg)

    def on_propose(self, msg_id: int, dialogue_id: int, origin: str, target: int, proposals: PROPOSE_TYPES) -> None:
        """
        On propose event handler.

        :param msg_id: the message id.
        :param dialogue_id: the dialogue id.
        :param origin: the public key of the sender.
        :param target: the message target.
        :param proposals: the proposals.
        :return: None
        """
        msg = FIPAMessage(to=self.public_key,
                          sender=origin,
                          message_id=msg_id,
                          dialogue_id=dialogue_id,
                          target=target,
                          performative=FIPAMessage.Performative.PROPOSE,
                          proposal=proposals)
        self.in_queue.put(msg)

    def on_accept(self, msg_id: int, dialogue_id: int, origin: str, target: int) -> None:
        """
        On accept event handler.

        :param msg_id: the message id.
        :param dialogue_id: the dialogue id.
        :param origin: the public key of the sender.
        :param target: the message target.
        :return: None
        """
        performative = FIPAMessage.Performative.MATCH_ACCEPT if msg_id == 4 and target == 3 else FIPAMessage.Performative.ACCEPT
        msg = FIPAMessage(to=self.public_key,
                          sender=origin,
                          message_id=msg_id,
                          dialogue_id=dialogue_id,
                          target=target,
                          performative=performative)
        self.in_queue.put(msg)

    def on_decline(self, msg_id: int, dialogue_id: int, origin: str, target: int) -> None:
        """
        On decline event handler.

        :param msg_id: the message id.
        :param dialogue_id: the dialogue id.
        :param origin: the public key of the sender.
        :param target: the message target.
        :return: None
        """
        msg = FIPAMessage(to=self.public_key,
                          sender=origin,
                          message_id=msg_id,
                          dialogue_id=dialogue_id,
                          target=target,
                          performative=FIPAMessage.Performative.DECLINE)
        self.in_queue.put(msg)

    def on_search_result(self, search_id: int, agents: List[str]) -> None:
        """
        On accept event handler.

        :param search_id: the search id.
        :param agents: the list of agents.
        :return: None
        """
        self.mail_stats.search_end(search_id, len(agents))
        msg = OEFMessage(to=self.public_key,
                         sender=None,
                         oef_type=OEFMessage.Type.SEARCH_RESULT,
                         id=search_id,
                         agents=agents)
        self.in_queue.put(msg)

    def on_oef_error(self, answer_id: int, operation: OEFErrorOperation) -> None:
        """
        On oef error event handler.

        :param answer_id: the answer id.
        :param operation: the error operation.
        :return: None
        """
        msg = OEFMessage(to=self.public_key,
                         sender=None,
                         oef_type=OEFMessage.Type.OEF_ERROR,
                         id=answer_id,
                         operation=operation)
        self.in_queue.put(msg)

    def on_dialogue_error(self, answer_id: int, dialogue_id: int, origin: str) -> None:
        """
        On dialogue error event handler.

        :param answer_id: the answer id.
        :param dialogue_id: the dialogue id.
        :param origin: the message sender.
        :return: None
        """
        msg = OEFMessage(to=self.public_key,
                         sender=None,
                         oef_type=OEFMessage.Type.DIALOGUE_ERROR,
                         id=answer_id,
                         dialogue_id=dialogue_id,
                         origin=origin)
        self.in_queue.put(msg)

    def send(self, msg: Message) -> None:
        """
        Send message handler.

        :param msg: the message.
        :return: None
        """
        if msg.protocol_id == "oef":
            self.send_oef_message(msg)
        elif msg.protocol_id == "fipa":
            self.send_fipa_message(msg)
        elif msg.protocol_id == "bytes":
            self.send_message(msg.get("id"), msg.get("dialogue_id"), msg.to, msg.get("content"))
        elif msg.protocol_id == "default":
            self.send_message(msg.get("id"), 0, msg.to, msg.get("content"))
        else:
            raise ValueError("Cannot send message.")

    def send_oef_message(self, msg: Message) -> None:
        """
        Send oef message handler.

        :param msg: the message.
        :return: None
        """
        oef_type = msg.get("type")
        if oef_type == OEFMessage.Type.REGISTER_SERVICE:
            id = msg.get("id")
            service_description = msg.get("service_description")
            service_id = msg.get("service_id")
            self.register_service(id, service_description, service_id)
        elif oef_type == OEFMessage.Type.REGISTER_AGENT:
            id = msg.get("id")
            agent_description = msg.get("agent_description")
            self.register_agent(id, agent_description)
        elif oef_type == OEFMessage.Type.UNREGISTER_SERVICE:
            id = msg.get("id")
            service_description = msg.get("service_description")
            service_id = msg.get("service_id")
            self.unregister_service(id, service_description, service_id)
        elif oef_type == OEFMessage.Type.UNREGISTER_AGENT:
            id = msg.get("id")
            self.unregister_agent(id)
        elif oef_type == OEFMessage.Type.SEARCH_AGENTS:
            id = msg.get("id")
            query = msg.get("query")
            self.search_agents(id, query)
        elif oef_type == OEFMessage.Type.SEARCH_SERVICES:
            id = msg.get("id")
            query = msg.get("query")
            self.mail_stats.search_start(id)
            self.search_services(id, query)
        else:
            raise ValueError("OEF request not recognized.")

    def send_fipa_message(self, msg: Message) -> None:
        """
        Send fipa message handler.

        :param msg: the message.
        :return: None
        """
        id = msg.get("id")
        dialogue_id = msg.get("dialogue_id")
        destination = msg.to
        target = msg.get("target")
        performative = msg.get("performative")
        if performative == FIPAMessage.Performative.CFP:
            query = msg.get("query")
            self.send_cfp(id, dialogue_id, destination, target, query)
        elif performative == FIPAMessage.Performative.PROPOSE:
            proposal = msg.get("proposal")
            self.send_propose(id, dialogue_id, destination, target, proposal)
        elif performative == FIPAMessage.Performative.ACCEPT:
            self.send_accept(id, dialogue_id, destination, target)
        elif performative == FIPAMessage.Performative.MATCH_ACCEPT:
            self.send_accept(id, dialogue_id, destination, target)
        elif performative == FIPAMessage.Performative.DECLINE:
            self.send_decline(id, dialogue_id, destination, target)
        else:
            raise ValueError("OEF FIPA message not recognized.")


class OEFConnection(Connection):
    """The OEFConnection connects the to the mailbox."""

    def __init__(self, oef_proxy: OEFProxy):
        """
        Initialize.

        :param oef_proxy: the OEFProxy
        """
        super().__init__()

        self.bridge = OEFChannel(oef_proxy, self.in_queue)

        self._stopped = True
        self.in_thread = Thread(target=self.bridge.run)
        self.out_thread = Thread(target=self._fetch)

    def _fetch(self) -> None:
        """
        Fetch the messages from the outqueue and send them.

        :return: None
        """
        while not self._stopped:
            try:
                msg = self.out_queue.get(block=True, timeout=1.0)
                self._send(msg)
            except Empty:
                pass

    def connect(self) -> None:
        """
        Connect to the bridge.

        :return: None
        """
        if self._stopped:
            self._stopped = False
            self.bridge.connect()
            self.in_thread.start()
            self.out_thread.start()

    def disconnect(self) -> None:
        """
        Disconnect from the bridge.

        :return: None
        """
        if self.bridge.is_active():
            self.bridge.stop()

        self._stopped = True
        self.in_thread.join()
        self.out_thread.join()
        self.in_thread = Thread(target=self.bridge.run)
        self.out_thread = Thread(target=self._fetch)
        self.bridge.disconnect()

    @property
    def is_established(self) -> bool:
        """Get the connection status."""
        return self.bridge.is_connected()

    def _send(self, msg: Message) -> None:
        """
        Send messages.

        :return: None
        """
        self.bridge.send(msg)


class OEFMailBox(MailBox):
    """The OEF mail box."""

    def __init__(self, oef_proxy: OEFProxy):
        """
        Initialize.

        :param oef_proxy: the oef proxy.
        """
        connection = OEFConnection(oef_proxy)
        super().__init__(connection)

    @property
    def mail_stats(self) -> MailStats:
        """Get the mail stats object."""
        return self._connection.bridge.mail_stats


class OEFNetworkMailBox(OEFMailBox):
    """The OEF network mail box."""

    def __init__(self, public_key: str, oef_addr: str, oef_port: int = 10000):
        """
        Initialize.

        :param public_key: the public key of the agent.
        :param oef_addr: the OEF address.
        :param oef_port: the oef port.
        """
        super().__init__(OEFNetworkProxy(public_key, oef_addr, oef_port, loop=asyncio.new_event_loop()))

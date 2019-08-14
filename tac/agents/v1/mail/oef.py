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
from typing import List, Union, Dict

from oef.agents import Agent
from oef.core import OEFProxy
from oef.messages import OEFErrorOperation, CFP_TYPES, PROPOSE_TYPES
from oef.proxy import OEFNetworkProxy

from tac.agents.v1.mail.base import Connection, MailBox
from tac.agents.v1.mail.messages import OEFRegisterServiceRequest, OEFRegisterAgentRequest, \
    OEFUnregisterServiceRequest, OEFUnregisterAgentRequest, OEFSearchAgentsRequest, OEFSearchServicesRequest, \
    OEFRequest, OEFAgentMessage, OEFAgentByteMessage, OEFAgentFIPAMessage, OEFAgentCfp, OEFAgentPropose, OEFAgentAccept, \
    OEFAgentDecline, OEFSearchResult, OEFGenericError, OEFDialogueError

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

    def __init__(self, oef_proxy: OEFProxy, in_queue: Queue):
        super().__init__(oef_proxy)
        self.in_queue = in_queue
        self.mail_stats = MailStats()

    def is_connected(self):
        return self._oef_proxy.is_connected()

    def on_message(self, msg_id: int, dialogue_id: int, origin: str, content: bytes):
        self.in_queue.put(OEFAgentByteMessage(msg_id, dialogue_id, origin, content))

    def on_cfp(self, msg_id: int, dialogue_id: int, origin: str, target: int, query: CFP_TYPES):
        self.in_queue.put(OEFAgentCfp(msg_id, dialogue_id, origin, target, query))

    def on_propose(self, msg_id: int, dialogue_id: int, origin: str, target: int, proposals: PROPOSE_TYPES):
        self.in_queue.put(OEFAgentPropose(msg_id, dialogue_id, origin, target, proposals))

    def on_accept(self, msg_id: int, dialogue_id: int, origin: str, target: int):
        self.in_queue.put(OEFAgentAccept(msg_id, dialogue_id, origin, target))

    def on_decline(self, msg_id: int, dialogue_id: int, origin: str, target: int):
        self.in_queue.put(OEFAgentDecline(msg_id, dialogue_id, origin, target))

    def on_search_result(self, search_id: int, agents: List[str]):
        self.mail_stats.search_end(search_id, len(agents))
        self.in_queue.put(OEFSearchResult(search_id, agents))

    def on_oef_error(self, answer_id: int, operation: OEFErrorOperation):
        self.in_queue.put(OEFGenericError(answer_id, operation))

    def on_dialogue_error(self, answer_id: int, dialogue_id: int, origin: str):
        self.in_queue.put(OEFDialogueError(answer_id, dialogue_id, origin))

    def send(self, msg: Union[OEFRequest, OEFAgentMessage]):
        if isinstance(msg, OEFRequest):
            self.send_oef_request(msg)
        elif isinstance(msg, OEFAgentMessage):
            self.send_oef_agent_message(msg)
        else:
            raise ValueError("Cannot send message.")

    def send_oef_request(self, msg: OEFRequest):
        if isinstance(msg, OEFRegisterServiceRequest):
            self.register_service(msg.msg_id, msg.agent_description, msg.service_id)
        elif isinstance(msg, OEFRegisterAgentRequest):
            self.register_agent(msg.msg_id, msg.agent_description)
        elif isinstance(msg, OEFUnregisterServiceRequest):
            self.unregister_service(msg.msg_id, msg.agent_description, msg.service_id)
        elif isinstance(msg, OEFUnregisterAgentRequest):
            self.unregister_agent(msg.msg_id)
        elif isinstance(msg, OEFSearchAgentsRequest):
            self.search_agents(msg.search_id, msg.query)
        elif isinstance(msg, OEFSearchServicesRequest):
            self.mail_stats.search_start(msg.search_id)
            self.search_services(msg.search_id, msg.query)
        else:
            raise ValueError("OEF request not recognized.")

    def send_oef_agent_message(self, msg: OEFAgentMessage):
        if isinstance(msg, OEFAgentByteMessage):
            self.send_message(msg.msg_id, msg.dialogue_id, msg.destination, msg.content)
        elif isinstance(msg, OEFAgentFIPAMessage):
            self.send_fipa_message(msg)
        else:
            raise ValueError("OEF Agent message not recognized.")

    def send_fipa_message(self, msg: OEFAgentFIPAMessage):
        if isinstance(msg, OEFAgentCfp):
            self.send_cfp(msg.msg_id, msg.dialogue_id, msg.destination, msg.target, msg.query)
        elif isinstance(msg, OEFAgentPropose):
            self.send_propose(msg.msg_id, msg.dialogue_id, msg.destination, msg.target, msg.proposal)
        elif isinstance(msg, OEFAgentAccept):
            self.send_accept(msg.msg_id, msg.dialogue_id, msg.destination, msg.target)
        elif isinstance(msg, OEFAgentDecline):
            self.send_decline(msg.msg_id, msg.dialogue_id, msg.destination, msg.target)
        else:
            raise ValueError("OEF FIPA message not recognized.")

    def is_active(self) -> bool:
        return self._oef_proxy._active_loop


class OEFConnection(Connection):

    def __init__(self, oef_proxy: OEFProxy):
        super().__init__()

        self.bridge = OEFChannel(oef_proxy, self.in_queue)

        self._stopped = True
        self.in_thread = Thread(target=self.bridge.run)
        self.out_thread = Thread(target=self._fetch)

    def _fetch(self):
        while not self._stopped:
            try:
                msg = self.out_queue.get(block=True, timeout=1.0)
                self.send(msg)
            except Empty:
                pass

    def connect(self):
        if self._stopped:
            self._stopped = False
            self.bridge.connect()
            self.in_thread.start()
            self.out_thread.start()

    def disconnect(self):
        if self.bridge.is_active():
            self.bridge.stop()

        self._stopped = True
        self.in_thread.join()
        self.out_thread.join()
        self.bridge.disconnect()

    @property
    def is_established(self) -> bool:
        return self.bridge.is_connected()

    def send(self, msg: Union[OEFRequest, OEFAgentMessage]):
        self.bridge.send(msg)


class OEFMailBox(MailBox):

    def __init__(self, proxy: OEFProxy):
        connection = OEFConnection(proxy)
        super().__init__(connection)

    @property
    def mail_stats(self) -> MailStats:
        return self._connection.bridge.mail_stats


class OEFNetworkMailBox(OEFMailBox):

    def __init__(self, public_key: str, oef_addr: str, port: int = 10000):
        super().__init__(OEFNetworkProxy(public_key, oef_addr, port, loop=asyncio.new_event_loop()))

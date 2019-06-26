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
from typing import Optional, Union

from oef.messages import CFP, Decline, Propose, Accept, Message as SimpleMessage, \
    SearchResult, OEFErrorMessage, DialogueErrorMessage

from tac.agents.v2.agent import Agent
from tac.agents.v2.mail import FIPAMailBox, InBox, OutBox
from tac.agents.v2.base.game_instance import GameInstance, GamePhase
from tac.agents.v2.base.helpers import is_oef_message, is_controller_message
from tac.agents.v2.base.handlers import DialogueHandler, ControllerHandler, OEFHandler
from tac.agents.v2.base.strategy import Strategy
from tac.gui.dashboards.agent import AgentDashboard

OEFMessage = Union[SearchResult, OEFErrorMessage, DialogueErrorMessage]
ControllerMessage = SimpleMessage
AgentMessage = Union[SimpleMessage, CFP, Propose, Accept, Decline]
Message = Union[OEFMessage, ControllerMessage, AgentMessage]


class ParticipantAgent(Agent):

    def __init__(self, name: str,
                 oef_addr: str,
                 oef_port: int,
                 strategy: Strategy,
                 services_interval: int = 10,
                 pending_transaction_timeout: int = 30,
                 dashboard: Optional[AgentDashboard] = None,
                 private_key_pem_path: Optional[str] = None):
        """
        Initialize a participant agent.
        :param name: the name of the agent.
        :param oef_addr: the TCP/IP address of the OEF node.
        :param oef_port: the TCP/IP port of the OEF node.
        :param strategy: the strategy object that specify the behaviour during the competition.
        :param services_interval: the number of seconds between different searches.
        :param pending_transaction_timeout: the timeout for cleanup of pending negotiations and unconfirmed transactions.
        :param dashboard: a Visdom dashboard to visualize agent statistics during the competition.
        :param private_key_pem_path: the path to a private key in PEM format.
        """
        super().__init__(name, oef_addr, oef_port, private_key_pem_path)
        self.mail_box = FIPAMailBox(self.crypto.public_key, oef_addr, oef_port)
        self.in_box = InBox(self.mail_box)
        self.out_box = OutBox(self.mail_box)

        self._is_competing = False  # type: bool
        self._game_instance = GameInstance(name, strategy, services_interval, pending_transaction_timeout, dashboard)  # type: Optional[GameInstance]

        self.controller_handler = ControllerHandler(self.crypto, self.liveness, self.game_instance, self.out_box, self.name)
        self.oef_handler = OEFHandler(self.crypto, self.liveness, self.game_instance, self.out_box, self.name)
        self.dialogue_handler = DialogueHandler(self.crypto, self.liveness, self.game_instance, self.out_box, self.name)

    @property
    def game_instance(self) -> GameInstance:
        return self._game_instance

    @property
    def is_competing(self) -> bool:
        return self._is_competing

    def act(self) -> None:
        """
        Performs actions.

        :return: None
        """
        if not self.is_competing:
            self.oef_handler.search_for_tac()
            self._is_competing = True
        if self.game_instance.game_phase == GamePhase.GAME:
            if self.game_instance.is_time_to_update_services():
                self.oef_handler.update_services()
            if self.game_instance.is_time_to_search_services():
                self.oef_handler.search_services()

        self.out_box.send_nowait()

    def react(self) -> None:
        """
        Reacts to incoming events.

        :return: None
        """
        msg = self.in_box.get_some_wait()  # type: Optional[Message]
        if msg is not None:
            if is_oef_message(msg):
                msg: OEFMessage
                self.oef_handler.handle_oef_message(msg)
            elif is_controller_message(msg, self.crypto):
                msg: ControllerMessage
                self.controller_handler.handle_controller_message(msg)
            else:
                msg: AgentMessage
                self.dialogue_handler.handle_dialogue_message(msg)

            self.out_box.send_nowait()

    def stop(self) -> None:
        super().stop()
        self.game_instance.lock_manager.stop()

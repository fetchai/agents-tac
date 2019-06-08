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
import asyncio
from typing import Optional, Union

from oef.messages import CFP, Decline, Propose, Accept, Message as SimpleMessage, \
    SearchResult, OEFErrorMessage, DialogueErrorMessage

from tac.experimental.core.agent import Agent
from tac.experimental.core.mail import FIPAMailBox, InBox, OutBox
from tac.experimental.core.tac.game_instance import GameInstance, GamePhase
from tac.experimental.core.tac.helpers import is_oef_message, is_controller_message
from tac.experimental.core.tac.handlers import DialogueHandler, ControllerHandler, OEFHandler

OEFMessage = Union[SearchResult, OEFErrorMessage, DialogueErrorMessage]
ControllerMessage = SimpleMessage
AgentMessage = Union[SimpleMessage, CFP, Propose, Accept, Decline]
Message = Union[OEFMessage, ControllerMessage, AgentMessage]


class ParticipantAgent(Agent):

    def __init__(self, name: str, oef_addr: str, oef_port: int = 3333, is_world_modeling: bool = False):
        super().__init__(name, oef_addr, oef_port)
        self.mail_box = FIPAMailBox(self.crypto.public_key, oef_addr, oef_port, loop=asyncio.get_event_loop())
        self.in_box = InBox(self.mail_box)
        self.out_box = OutBox(self.mail_box)

        self._is_competing = False  # type: bool
        self._game_instance = GameInstance(name, is_world_modeling)  # type: Optional[GameInstance]

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
        self.out_box.send_nowait()

        if not self.is_competing:
            self.oef_handler.search_for_tac()
            self._is_competing = True
        if self.game_instance.game_phase == GamePhase.GAME:
            if self.game_instance.is_time_to_update_services():
                self.oef_handler.update_services()
            if self.game_instance.ist_time_to_search_services():
                self.oef_handler.search_services()

    def react(self) -> None:
        """
        Reacts to incoming events. This is blocking.

        :return: None
        """
        msg = self.in_box.get_wait()  # type: Message

        if is_oef_message(msg):
            msg: OEFMessage
            self.oef_handler.handle_oef_message(msg)
        elif is_controller_message(msg, self.crypto):
            msg: ControllerMessage
            self.controller_handler.handle_controller_message(msg)
        else:
            msg: AgentMessage
            self.dialogue_handler.handle_dialogue_message(msg)

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
from abc import abstractmethod
from typing import List, Optional, Any, Dict, Union

from oef.messages import CFP, Decline, Propose, Accept, Message as SimpleMessage, \
    SearchResult, OEFErrorMessage, DialogueErrorMessage

Action = Any
OEFMessage = Union[SearchResult, OEFErrorMessage, DialogueErrorMessage]
ControllerMessage = SimpleMessage
AgentMessage = Union[SimpleMessage, CFP, Propose, Accept, Decline]
Message = Union[OEFMessage, ControllerMessage, AgentMessage]


class DialogueLabel:
    """Identifier for dialogues."""

    def __init__(self, dialogue_id: int, agent_pbk: str):
        """
        Initialize a dialogue label.
        :param dialogue_id: the id of the dialogue.
        :param agent_pbk: the interlocutor agent's public key.
        """
        self._dialogue_id = dialogue_id
        self._agent_pbk = agent_pbk

    @property
    def dialogue_id(self) -> int:
        return self._dialogue_id

    @property
    def agent_pbk(self) -> str:
        return self._agent_pbk

    def __eq__(self, other):
        if type(other) == DialogueLabel:
            return self._dialogue_id == other.dialogue_id and self._agent_pbk == other.agent_pbk
        else:
            return False

    def __hash__(self):
        return hash((self.dialogue_id, self.agent_pbk))


class ProtocolInterface:

    @abstractmethod
    def check_message(self, msg: AgentMessage) -> bool:
        pass


class BehaviourInterface:

    @abstractmethod
    def dispatch_to_handler(self, msg: AgentMessage) -> Optional[Action]:
        pass


class Dialogue(ProtocolInterface, BehaviourInterface):

    def __init__(self, dialogue_label: DialogueLabel):  # agent: 'TACParticipantAgent'
        self.dialogue_label = dialogue_label
        self.messages = []  # type: List[AgentMessage]


class Dialogues:

    def __init__(self):
        self.dialogues = {}  # type: Dict[DialogueLabel, Dialogue]

    def is_dialogue_registered(self, dialogue_label) -> bool:
        return dialogue_label in self.dialogues

    def get_dialogue(self, dialogue_label: DialogueLabel) -> Dialogue:
        return self.dialogues[dialogue_label]

    def register_dialogue(self, dialogue: Dialogue) -> None:
        self.dialogues[dialogue.dialogue_label] = dialogue

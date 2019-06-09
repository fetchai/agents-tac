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

    def __init__(self, dialogue_id: int, dialogue_starter_pbk: str):
        """
        Initialize a dialogue label.
        :param dialogue_id: the id of the dialogue.
        :param dialogue_starter_pbk: the pbk of the agent which started the dialogue.
        """
        self._dialogue_id = dialogue_id
        self._dialogue_starter_pbk = dialogue_starter_pbk

    @property
    def dialogue_id(self) -> int:
        return self._dialogue_id

    @property
    def dialogue_starter_pbk(self) -> str:
        return self._dialogue_starter_pbk

    def __eq__(self, other):
        if type(other) == DialogueLabel:
            return self._dialogue_id == other.dialogue_id and self._dialogue_starter_pbk == other.dialogue_starter_pbk
        else:
            return False

    def __hash__(self):
        return hash((self.dialogue_id, self.dialogue_starter_pbk))


class ProtocolInterface:

    @abstractmethod
    def check_message(self, msg: AgentMessage) -> bool:
        """
        Checks the message against the protocol
        """


class BehaviourInterface:

    @abstractmethod
    def dispatch_to_handler(self, msg: AgentMessage) -> Optional[Action]:
        """
        Dispatches to correct handler
        """


class Dialogue(ProtocolInterface, BehaviourInterface):

    def __init__(self, dialogue_label: DialogueLabel, is_seller: bool):
        self.dialogue_label = dialogue_label
        self.is_seller = is_seller
        self.messages = []  # type: List[AgentMessage]

    def dispatch_to_handler(self, msg: AgentMessage):
        return None

    def check_message(self, msg: AgentMessage):
        return True


class Dialogues:

    def __init__(self):
        self._dialogues = {}  # type: Dict[DialogueLabel, Dialogue]
        self._dialogues_as_seller = {}  # type: Dict[DialogueLabel, Dialogue]
        self._dialogues_as_buyer = {}  # type: Dict[DialogueLabel, Dialogue]
        self.dialogue_id = 0

    @property
    def dialogues(self) -> Dialogue:
        return self._dialogues

    @property
    def dialogues_as_seller(self):
        return self._dialogues_as_seller

    @property
    def dialogues_as_buyer(self):
        return self._dialogues_as_buyer

    def is_dialogue_registered(self, dialogue_id: int, opponent_pbk: str, agent_pbk: str) -> DialogueLabel:
        self_initiated_dialogue = DialogueLabel(dialogue_id, agent_pbk)
        other_initiated_dialogue = DialogueLabel(dialogue_id, opponent_pbk)
        return self_initiated_dialogue in self.dialogues != other_initiated_dialogue in self.dialogues

    def get_dialogue(self, dialogue_id: int, opponent_pbk: str, agent_pbk: str) -> Dialogue:
        self_initiated_dialogue = DialogueLabel(dialogue_id, agent_pbk)
        other_initiated_dialogue = DialogueLabel(dialogue_id, opponent_pbk)
        dialogue_label = self_initiated_dialogue if self_initiated_dialogue in self.dialogues else other_initiated_dialogue
        return self.dialogues[dialogue_label]

    def next_dialogue_id(self) -> int:
        """
        Increments the id and returns it.
        """
        self.dialogue_id += 1
        return self.dialogue_id

    def create(self, dialogue_starter_pbk: str, is_seller: bool) -> DialogueLabel:
        """
        Saves the dialogue id.

        :param dialogue_starter_pbk: the pbk of the agent which started the dialogue
        :param is_seller: boolean indicating the agent role

        :return: None
        """
        dialogue_label = DialogueLabel(self.next_dialogue_id(), dialogue_starter_pbk)
        assert dialogue_label not in self.dialogues
        dialogue = Dialogue(dialogue_label, is_seller)
        if is_seller:
            assert dialogue_label not in self.dialogues_as_seller
            self._dialogues_as_seller.update({dialogue_label: dialogue})
        else:
            assert dialogue_label not in self.dialogues_as_buyer
            self._dialogues_as_buyer.update({dialogue_label: dialogue})
        self.dialogues.update({dialogue_label: dialogue})
        return dialogue

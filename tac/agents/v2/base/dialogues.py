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
from typing import List, Any, Dict, Union

from oef.messages import CFP, Decline, Propose, Accept, Message as SimpleMessage, \
    SearchResult, OEFErrorMessage, DialogueErrorMessage
from oef.query import Query

Action = Any
OEFMessage = Union[SearchResult, OEFErrorMessage, DialogueErrorMessage]
ControllerMessage = SimpleMessage
AgentMessage = Union[SimpleMessage, CFP, Propose, Accept, Decline]
Message = Union[OEFMessage, ControllerMessage, AgentMessage]

STARTING_MESSAGE_ID = 1
STARTING_MESSAGE_TARGET = 0


class DialogueLabel:
    """Identifier for dialogues."""

    def __init__(self, dialogue_id: int, dialogue_opponent_pbk: str, dialogue_starter_pbk: str):
        """
        Initialize a dialogue label.
        :param dialogue_id: the id of the dialogue.
        :param dialogue_opponent_pbk: the pbk of the agent with which the dialogue is kept.
        :param dialogue_starter_pbk: the pbk of the agent which started the dialogue.
        """
        self._dialogue_id = dialogue_id
        self._dialogue_opponent_pbk = dialogue_opponent_pbk
        self._dialogue_starter_pbk = dialogue_starter_pbk

    @property
    def dialogue_id(self) -> int:
        return self._dialogue_id

    @property
    def dialogue_opponent_pbk(self) -> str:
        return self._dialogue_opponent_pbk

    @property
    def dialogue_starter_pbk(self) -> str:
        return self._dialogue_starter_pbk

    def __eq__(self, other):
        if type(other) == DialogueLabel:
            return self._dialogue_id == other.dialogue_id and self._dialogue_starter_pbk == other.dialogue_starter_pbk and self._dialogue_opponent_pbk == other.dialogue_opponent_pbk
        else:
            return False

    def __hash__(self):
        return hash((self.dialogue_id, self.dialogue_opponent_pbk, self.dialogue_starter_pbk))


class ProtocolInterface:

    @abstractmethod
    def is_message_consistent(self, msg: AgentMessage) -> bool:
        """
        Checks the message against the protocol.
        """

    @abstractmethod
    def outgoing_extend(self, msg: AgentMessage) -> None:
        """
        Adds a new outgoing message to the dialogue.

        :param msg: any message allowed in the dialogue
        """

    @abstractmethod
    def incoming_extend(self, msg: AgentMessage) -> None:
        """
        Adds a new incoming message to the dialogue.

        :param msg: any message allowed in the dialogue
        """

    @abstractmethod
    def cfp(self, query: Query) -> CFP:
        """
        Creates a cfp.

        :param query: the query
        """


class Dialogue(ProtocolInterface):

    def __init__(self, dialogue_label: DialogueLabel, is_seller: bool):
        self.dialogue_label = dialogue_label
        self.is_seller = is_seller
        self.outgoing_messages = []  # type: List[AgentMessage]
        self.incoming_messages = []  # type: List[AgentMessage]

    def is_message_consistent(self, msg: AgentMessage):
        """
        """
        last_sent_message = self.outgoing_messages[-1:]
        if last_sent_message == []:
            result = False
        elif (isinstance(last_sent_message, CFP) and isinstance(msg, Propose)) or \
             (isinstance(last_sent_message, Propose) and isinstance(msg, Accept)) or \
             (isinstance(last_sent_message, Propose) and isinstance(msg, Decline)) or \
             (isinstance(last_sent_message, Accept) and isinstance(msg, Accept)):
            result = True
        else:
            result = False
        return result

    def outgoing_extend(self, messages: List[AgentMessage]) -> None:
        self.outgoing_messages.extend(messages)

    def incoming_extend(self, messages: List[AgentMessage]) -> None:
        self.incoming_messages.extend(messages)

    def role(self) -> str:
        role = 'seller' if self.is_seller else 'buyer'
        return role

    def cfp(self, query: Query) -> CFP:
        """
        Creates a cfp.

        :param query: the query
        """
        cfp = CFP(STARTING_MESSAGE_ID, self.dialogue_label.dialogue_id, self.dialogue_label.dialogue_opponent_pbk, STARTING_MESSAGE_TARGET, query)
        self.outgoing_extend([cfp])
        return cfp


class Dialogues:

    def __init__(self):
        self._dialogues = {}  # type: Dict[DialogueLabel, Dialogue]
        self._dialogues_as_seller = {}  # type: Dict[DialogueLabel, Dialogue]
        self._dialogues_as_buyer = {}  # type: Dict[DialogueLabel, Dialogue]
        self.dialogue_id = 0

    @property
    def dialogues(self) -> Dict[DialogueLabel, Dialogue]:
        return self._dialogues

    @property
    def dialogues_as_seller(self) -> Dict[DialogueLabel, Dialogue]:
        return self._dialogues_as_seller

    @property
    def dialogues_as_buyer(self) -> Dict[DialogueLabel, Dialogue]:
        return self._dialogues_as_buyer

    def is_permitted_for_new_dialogue(self, msg: AgentMessage, known_pbks: List[str]) -> bool:
        result = isinstance(msg, CFP) and (msg.destination in known_pbks)
        return result

    def is_dialogue_registered(self, dialogue_id: int, opponent_pbk: str, agent_pbk: str) -> DialogueLabel:
        self_initiated_dialogue = DialogueLabel(dialogue_id, opponent_pbk, agent_pbk)
        other_initiated_dialogue = DialogueLabel(dialogue_id, opponent_pbk, opponent_pbk)
        return (self_initiated_dialogue in self.dialogues) is not (other_initiated_dialogue in self.dialogues)

    def get_dialogue(self, dialogue_id: int, opponent_pbk: str, agent_pbk: str) -> Dialogue:
        self_initiated_dialogue = DialogueLabel(dialogue_id, opponent_pbk, agent_pbk)
        other_initiated_dialogue = DialogueLabel(dialogue_id, opponent_pbk, opponent_pbk)
        dialogue_label = self_initiated_dialogue if self_initiated_dialogue in self.dialogues else other_initiated_dialogue
        return self.dialogues[dialogue_label]

    def next_dialogue_id(self) -> int:
        """
        Increments the id and returns it.
        """
        self.dialogue_id += 1
        return self.dialogue_id

    def create(self, dialogue_opponent_pbk: str, dialogue_starter_pbk: str, is_seller: bool) -> Dialogue:
        """
        Create a new dialogue.

        :param dialogue_opponent_pbk: the pbk of the agent with which the dialogue is kept.
        :param dialogue_starter_pbk: the pbk of the agent which started the dialogue
        :param is_seller: boolean indicating the agent role

        :return: the created dialogue.
        """
        dialogue_label = DialogueLabel(self.next_dialogue_id(), dialogue_opponent_pbk, dialogue_starter_pbk)
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

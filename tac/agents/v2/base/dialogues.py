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
from typing import List, Any, Dict, Union

from oef.messages import CFP, Decline, Propose, Accept, Message as ByteMessage, \
    SearchResult, OEFErrorMessage, DialogueErrorMessage
from tac.agents.v2.mail import OutContainer

Action = Any
OEFMessage = Union[SearchResult, OEFErrorMessage, DialogueErrorMessage]
ControllerMessage = ByteMessage
AgentMessage = Union[ByteMessage, CFP, Propose, Accept, Decline, OutContainer]
Message = Union[OEFMessage, ControllerMessage, AgentMessage]

logger = logging.getLogger(__name__)


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

    def __eq__(self, other) -> bool:
        if type(other) == DialogueLabel:
            return self._dialogue_id == other.dialogue_id and self._dialogue_starter_pbk == other.dialogue_starter_pbk and self._dialogue_opponent_pbk == other.dialogue_opponent_pbk
        else:
            return False

    def __hash__(self) -> str:
        return hash((self.dialogue_id, self.dialogue_opponent_pbk, self.dialogue_starter_pbk))


class Dialogue:
    """The dialogue maintains state of a dialogue and manages it."""

    def __init__(self, dialogue_label: DialogueLabel, is_seller: bool):
        """
        Initialize a dialogue label.

        :param dialogue_label: the identifier of the dialogue
        :param is_seller: indicates whether the agent associated with the dialogue is a seller or buyer
        """
        self._dialogue_label = dialogue_label
        self._is_seller = is_seller
        self._role = 'seller' if is_seller else 'buyer'
        self._outgoing_messages = []  # type: List[AgentMessage]
        self._outgoing_messages_controller = []  # type: List[AgentMessage]
        self._incoming_messages = []  # type: List[AgentMessage]

    @property
    def dialogue_label(self) -> DialogueLabel:
        return self._dialogue_label

    @property
    def is_seller(self) -> bool:
        return self._is_seller

    @property
    def role(self) -> str:
        return self._role

    def outgoing_extend(self, messages: List[AgentMessage]) -> None:
        """
        Extends the list of messages which keeps track of outgoing messages.

        :param messages: a list of messages to be added
        :return: None
        """
        for message in messages:
            if isinstance(message, OutContainer):
                self._outgoing_messages_controller.extend([message])
            else:
                self._outgoing_messages.extend([message])

    def incoming_extend(self, messages: List[AgentMessage]) -> None:
        """
        Extends the list of messages which keeps track of incoming messages.

        :param messages: a list of messages to be added
        :return: None
        """
        self._incoming_messages.extend(messages)

    def is_expecting_propose(self) -> bool:
        """
        Checks whether the dialogue is expecting a propose.

        :return: True if yes, False otherwise.
        """
        last_sent_message = self.outgoing_messages[-1:]
        result = (last_sent_message is not []) and isinstance(last_sent_message[0], CFP)
        return result

    def is_expecting_initial_accept(self) -> bool:
        """
        Checks whether the dialogue is expecting an initial accept.

        :return: True if yes, False otherwise.
        """
        last_sent_message = self.outgoing_messages[-1:]
        result = (last_sent_message is not []) and isinstance(last_sent_message[0], Propose)
        return result

    def is_expecting_matching_accept(self) -> bool:
        """
        Checks whether the dialogue is expecting a matching accept.

        :return: True if yes, False otherwise.
        """
        last_sent_message = self.outgoing_messages[-1:]
        result = (last_sent_message is not []) and isinstance(last_sent_message[0], Accept)
        return result

    def is_expecting_cfp_decline(self) -> bool:
        """
        Checks whether the dialogue is expecting an decline following a cfp.

        :return: True if yes, False otherwise.
        """
        last_sent_message = self.outgoing_messages[-1:]
        result = (last_sent_message is not []) and isinstance(last_sent_message[0], CFP)
        return result

    def is_expecting_propose_decline(self) -> bool:
        """
        Checks whether the dialogue is expecting an decline following a propose.

        :return: True if yes, False otherwise.
        """
        last_sent_message = self.outgoing_messages[-1:]
        result = (last_sent_message is not []) and isinstance(last_sent_message[0], Propose)
        return result


class Dialogues:
    """This class keeps track of all dialogues"""

    def __init__(self):
        """Initialize dialogues."""
        self._dialogues = {}  # type: Dict[DialogueLabel, Dialogue]
        self._dialogues_as_seller = {}  # type: Dict[DialogueLabel, Dialogue]
        self._dialogues_as_buyer = {}  # type: Dict[DialogueLabel, Dialogue]
        self._dialogue_id = 0

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
        """
        Checks whether an agent message is a CFP and from a known public key.

        :param msg: the agent message
        :param known_pbks: the list of known public keys
        :return: a boolean
        """
        result = isinstance(msg, CFP) and (msg.destination in known_pbks)
        return result

    def is_belonging_to_registered_dialogue(self, msg: AgentMessage, agent_pbk: str) -> DialogueLabel:
        """
        Checks whether an agent message is part of a registered dialogue.

        :param msg: the agent message
        :param agent_pbk: the public key of the agent
        """
        self_initiated_dialogue_label = DialogueLabel(msg.dialogue_id, msg.destination, agent_pbk)
        other_initiated_dialogue_label = DialogueLabel(msg.dialogue_id, msg.destination, msg.destination)
        result = False
        if isinstance(msg, Propose) and (msg.target == 1) and self_initiated_dialogue_label in self.dialogues:
            self_initiated_dialogue = self.dialogues[self_initiated_dialogue_label]
            result = self_initiated_dialogue.is_expecting_propose()
        elif isinstance(msg, Accept):
            if msg.target == 2 and other_initiated_dialogue_label in self.dialogues:
                other_initiated_dialogue = self.dialogues[other_initiated_dialogue_label]
                result = other_initiated_dialogue.is_expecting_initial_accept()
            elif msg.target == 3 and self_initiated_dialogue_label in self.dialogues:
                self_initiated_dialogue = self.dialogues[self_initiated_dialogue_label]
                result = self_initiated_dialogue.is_expecting_matching_accept()
        elif isinstance(msg, Decline):
            if msg.target == 1 and self_initiated_dialogue_label in self.dialogues:
                self_initiated_dialogue = self.dialogues[self_initiated_dialogue_label]
                result = self_initiated_dialogue.is_expecting_cfp_decline()
            elif msg.target == 2 and other_initiated_dialogue_label in self.dialogues:
                other_initiated_dialogue = self.dialogues[other_initiated_dialogue_label]
                result = self_initiated_dialogue.is_expecting_proposal_decline()
        return result

    def get_dialogue(self, msg: AgentMessage, agent_pbk: str) -> Dialogue:
        """
        Retrieves dialogue.

        :param msg: the agent message
        :param agent_pbk: the public key of the agent
        """
        self_initiated_dialogue_label = DialogueLabel(msg.dialogue_id, msg.destination, agent_pbk)
        other_initiated_dialogue_label = DialogueLabel(msg.dialogue_id, msg.destination, msg.destination)
        if isinstance(msg, Propose) and (msg.target == 1) and self_initiated_dialogue_label in self.dialogues:
            dialogue = self.dialogues[self_initiated_dialogue_label]
        elif isinstance(msg, Accept):
            if msg.target == 2 and other_initiated_dialogue_label in self.dialogues:
                dialogue = self.dialogues[other_initiated_dialogue_label]
            elif msg.target == 3 and self_initiated_dialogue_label in self.dialogues:
                dialogue = self.dialogues[self_initiated_dialogue_label]
            else:
                raise ValueError('Should have found dialogue.')
        elif isinstance(msg, Decline):
            if msg.target == 1 and self_initiated_dialogue_label in self.dialogues:
                dialogue = self.dialogues[self_initiated_dialogue_label]
            elif msg.target == 2 and other_initiated_dialogue_label in self.dialogues:
                dialogue = self.dialogues[other_initiated_dialogue_label]
            else:
                raise ValueError('Should have found dialogue.')
        else:
            raise ValueError('Should have found dialogue.')
        return dialogue

    def _next_dialogue_id(self) -> int:
        """
        Increments the id and returns it.

        :return: the next id
        """
        self._dialogue_id += 1
        return self._dialogue_id

    def create_self_initiated(self, dialogue_opponent_pbk: str, dialogue_starter_pbk: str, is_seller: bool) -> Dialogue:
        """
        Create a self initiated dialogue.

        :param dialogue_opponent_pbk: the pbk of the agent with which the dialogue is kept.
        :param dialogue_starter_pbk: the pbk of the agent which started the dialogue
        :param is_seller: boolean indicating the agent role

        :return: the created dialogue.
        """
        dialogue_label = DialogueLabel(self._next_dialogue_id(), dialogue_opponent_pbk, dialogue_starter_pbk)
        result = self._create(dialogue_label, is_seller)
        return result

    def create_opponent_initiated(self, dialogue_opponent_pbk: str, dialogue_id: int, is_seller: bool) -> Dialogue:
        """
        Save an opponent initiated dialogue.

        :param dialogue_opponent_pbk: the pbk of the agent with which the dialogue is kept.
        :param dialogue_id: the id of the dialogue
        :param is_seller: boolean indicating the agent role

        :return: the created dialogue.
        """
        dialogue_starter_pbk = dialogue_opponent_pbk
        dialogue_label = DialogueLabel(dialogue_id, dialogue_opponent_pbk, dialogue_starter_pbk)
        result = self._create(dialogue_label, is_seller)
        return result

    def _create(self, dialogue_label: DialogueLabel, is_seller: bool) -> Dialogue:
        """
        Create a dialogue.

        :param dialogue_label: the dialogue label
        :param is_seller: boolean indicating the agent role

        :return: the created dialogue.
        """
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

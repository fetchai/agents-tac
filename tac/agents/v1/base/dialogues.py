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

"""
This module contains the classes required for dialogue management.

- DialogueLabel: The dialogue label class acts as an identifier for dialogues.
- Dialogue: The dialogue class maintains state of a dialogue and manages it.
- Dialogues: The dialogues class keeps track of all dialogues.
"""

import logging
from typing import List, Any, Dict, Optional

from tac.agents.v1.mail.messages import Message, FIPAMessage

Action = Any
logger = logging.getLogger(__name__)

STARTING_MESSAGE_ID = 1
STARTING_MESSAGE_TARGET = 0


class DialogueLabel:
    """The dialogue label class acts as an identifier for dialogues."""

    def __init__(self, dialogue_id: int, dialogue_opponent_pbk: str, dialogue_starter_pbk: str) -> None:
        """
        Initialize a dialogue label.

        :param dialogue_id: the id of the dialogue.
        :param dialogue_opponent_pbk: the pbk of the agent with which the dialogue is kept.
        :param dialogue_starter_pbk: the pbk of the agent which started the dialogue.

        :return: None
        """
        self._dialogue_id = dialogue_id
        self._dialogue_opponent_pbk = dialogue_opponent_pbk
        self._dialogue_starter_pbk = dialogue_starter_pbk

    @property
    def dialogue_id(self) -> int:
        """Get the dialogue id."""
        return self._dialogue_id

    @property
    def dialogue_opponent_pbk(self) -> str:
        """Get the public key of the dialogue opponent."""
        return self._dialogue_opponent_pbk

    @property
    def dialogue_starter_pbk(self) -> str:
        """Get the public key of the dialogue starter."""
        return self._dialogue_starter_pbk

    def __eq__(self, other) -> bool:
        """Check for equality between two DialogueLabel objects."""
        if type(other) == DialogueLabel:
            return self._dialogue_id == other.dialogue_id and self._dialogue_starter_pbk == other.dialogue_starter_pbk and self._dialogue_opponent_pbk == other.dialogue_opponent_pbk
        else:
            return False

    def __hash__(self) -> int:
        """Turn object into hash."""
        return hash((self.dialogue_id, self.dialogue_opponent_pbk, self.dialogue_starter_pbk))


class Dialogue:
    """The dialogue class maintains state of a dialogue and manages it."""

    def __init__(self, dialogue_label: DialogueLabel, is_seller: bool) -> None:
        """
        Initialize a dialogue label.

        :param dialogue_label: the identifier of the dialogue
        :param is_seller: indicates whether the agent associated with the dialogue is a seller or buyer

        :return: None
        """
        self._dialogue_label = dialogue_label
        self._is_seller = is_seller
        self._is_self_initiated = dialogue_label.dialogue_opponent_pbk is not dialogue_label.dialogue_starter_pbk
        self._role = 'seller' if is_seller else 'buyer'
        self._outgoing_messages = []  # type: List[Message]
        self._outgoing_messages_controller = []  # type: List[Message]
        self._incoming_messages = []  # type: List[Message]

    @property
    def dialogue_label(self) -> DialogueLabel:
        """Get the dialogue lable."""
        return self._dialogue_label

    @property
    def is_seller(self) -> bool:
        """Check whether the agent acts as the seller in this dialogue."""
        return self._is_seller

    @property
    def is_self_initiated(self) -> bool:
        """Check whether the agent initiated the dialogue."""
        return self._is_self_initiated

    @property
    def role(self) -> str:
        """Get role of agent in dialogue."""
        return self._role

    def outgoing_extend(self, messages: List[Message]) -> None:
        """
        Extend the list of messages which keeps track of outgoing messages.

        :param messages: a list of messages to be added
        :return: None
        """
        for message in messages:
            self._outgoing_messages.extend([message])

    def incoming_extend(self, messages: List[Message]) -> None:
        """
        Extend the list of messages which keeps track of incoming messages.

        :param messages: a list of messages to be added
        :return: None
        """
        self._incoming_messages.extend(messages)

    def is_expecting_propose(self) -> bool:
        """
        Check whether the dialogue is expecting a propose.

        :return: True if yes, False otherwise.
        """
        last_sent_message = self._outgoing_messages[-1] if len(self._outgoing_messages) > 0 else None  # type: Optional[Message]
        result = (last_sent_message is not None) and last_sent_message.protocol_id == "fipa" and last_sent_message.get("type") == FIPAMessage.Performative.CFP
        return result

    def is_expecting_initial_accept(self) -> bool:
        """
        Check whether the dialogue is expecting an initial accept.

        :return: True if yes, False otherwise.
        """
        last_sent_message = self._outgoing_messages[-1] if len(self._outgoing_messages) > 0 else None  # type: Optional[Message]
        result = (last_sent_message is not None) and last_sent_message.protocol_id == "fipa" and last_sent_message.get("type") == FIPAMessage.Performative.PROPOSE
        return result

    def is_expecting_matching_accept(self) -> bool:
        """
        Check whether the dialogue is expecting a matching accept.

        :return: True if yes, False otherwise.
        """
        last_sent_message = self._outgoing_messages[-1] if len(self._outgoing_messages) > 0 else None  # type: Optional[Message]
        result = (last_sent_message is not None) and last_sent_message.protocol_id == "fipa" and last_sent_message.get("type") == FIPAMessage.Performative.ACCEPT
        return result

    def is_expecting_cfp_decline(self) -> bool:
        """
        Check whether the dialogue is expecting an decline following a cfp.

        :return: True if yes, False otherwise.
        """
        last_sent_message = self._outgoing_messages[-1] if len(self._outgoing_messages) > 0 else None  # type: Optional[Message]
        result = (last_sent_message is not None) and last_sent_message.protocol_id == "fipa" and last_sent_message.get("type") == FIPAMessage.Performative.CFP
        return result

    def is_expecting_propose_decline(self) -> bool:
        """
        Check whether the dialogue is expecting an decline following a propose.

        :return: True if yes, False otherwise.
        """
        last_sent_message = self._outgoing_messages[-1] if len(self._outgoing_messages) > 0 else None  # type: Optional[Message]
        result = (last_sent_message is not None) and last_sent_message.protocol_id == "fipa" and last_sent_message.get("type") == FIPAMessage.Performative.PROPOSE
        return result

    def is_expecting_accept_decline(self) -> bool:
        """
        Check whether the dialogue is expecting an decline following an accept.

        :return: True if yes, False otherwise.
        """
        last_sent_message = self._outgoing_messages[-1] if len(self._outgoing_messages) > 0 else None  # type: Optional[Message]
        result = (last_sent_message is not None) and last_sent_message.protocol_id == "fipa" and last_sent_message.get("type") == FIPAMessage.Performative.ACCEPT
        return result


class Dialogues:
    """The dialogues class keeps track of all dialogues."""

    def __init__(self) -> None:
        """
        Initialize dialogues.

        :return: None
        """
        self._dialogues = {}  # type: Dict[DialogueLabel, Dialogue]
        self._dialogues_as_seller = {}  # type: Dict[DialogueLabel, Dialogue]
        self._dialogues_as_buyer = {}  # type: Dict[DialogueLabel, Dialogue]
        self._dialogue_id = 0

    @property
    def dialogues(self) -> Dict[DialogueLabel, Dialogue]:
        """Get dictionary of dialogues in which the agent is engaged in."""
        return self._dialogues

    @property
    def dialogues_as_seller(self) -> Dict[DialogueLabel, Dialogue]:
        """Get dictionary of dialogues in which the agent acts as a seller."""
        return self._dialogues_as_seller

    @property
    def dialogues_as_buyer(self) -> Dict[DialogueLabel, Dialogue]:
        """Get dictionary of dialogues in which the agent acts as a buyer."""
        return self._dialogues_as_buyer

    def is_permitted_for_new_dialogue(self, msg: Message, known_pbks: List[str]) -> bool:
        """
        Check whether an agent message is permitted for a new dialogue.

        That is, the message has to
        - be a CFP,
        - have the correct msg id and message target, and
        - be from a known public key.

        :param msg: the agent message
        :param known_pbks: the list of known public keys

        :return: a boolean indicating whether the message is permitted for a new dialogue
        """
        protocol = msg.protocol_id
        msg_id = msg.get("id")
        target = msg.get("target")
        performative = msg.get("performative")

        result = protocol == "fipa"\
                 and performative == FIPAMessage.Performative.CFP \
                 and msg_id == STARTING_MESSAGE_ID\
                 and target == STARTING_MESSAGE_TARGET \
                 and (msg.sender in known_pbks)
        return result

    def is_belonging_to_registered_dialogue(self, msg: Message, agent_pbk: str) -> bool:
        """
        Check whether an agent message is part of a registered dialogue.

        :param msg: the agent message
        :param agent_pbk: the public key of the agent

        :return: boolean indicating whether the message belongs to a registered dialogue
        """
        assert msg.protocol_id == "fipa"
        dialogue_id = msg.get("dialogue_id")
        destination = msg.to
        target = msg.get("target")
        performative = msg.get("performative")
        self_initiated_dialogue_label = DialogueLabel(dialogue_id, destination, agent_pbk)
        other_initiated_dialogue_label = DialogueLabel(dialogue_id, destination, destination)
        result = False
        if performative == FIPAMessage.Performative.PROPOSE and target == 1 and self_initiated_dialogue_label in self.dialogues:
            self_initiated_dialogue = self.dialogues[self_initiated_dialogue_label]
            result = self_initiated_dialogue.is_expecting_propose()
        elif performative == FIPAMessage.Performative.ACCEPT:
            if target == 2 and other_initiated_dialogue_label in self.dialogues:
                other_initiated_dialogue = self.dialogues[other_initiated_dialogue_label]
                result = other_initiated_dialogue.is_expecting_initial_accept()
            elif target == 3 and self_initiated_dialogue_label in self.dialogues:
                self_initiated_dialogue = self.dialogues[self_initiated_dialogue_label]
                result = self_initiated_dialogue.is_expecting_matching_accept()
        elif performative == FIPAMessage.Performative.DECLINE:
            if target == 1 and self_initiated_dialogue_label in self.dialogues:
                self_initiated_dialogue = self.dialogues[self_initiated_dialogue_label]
                result = self_initiated_dialogue.is_expecting_cfp_decline()
            elif target == 2 and other_initiated_dialogue_label in self.dialogues:
                other_initiated_dialogue = self.dialogues[other_initiated_dialogue_label]
                result = other_initiated_dialogue.is_expecting_propose_decline()
            elif target == 3 and self_initiated_dialogue_label in self.dialogues:
                self_initiated_dialogue = self.dialogues[self_initiated_dialogue_label]
                result = self_initiated_dialogue.is_expecting_accept_decline()
        return result

    def get_dialogue(self, msg: Message, agent_pbk: str) -> Dialogue:
        """
        Retrieve dialogue.

        :param msg: the agent message
        :param agent_pbk: the public key of the agent

        :return: the dialogue
        """
        assert msg.protocol_id == "fipa"
        dialogue_id = msg.get("dialogue_id")
        destination = msg.to
        target = msg.get("target")
        performative = msg.get("performative")
        self_initiated_dialogue_label = DialogueLabel(dialogue_id, destination, agent_pbk)
        other_initiated_dialogue_label = DialogueLabel(dialogue_id, destination, destination)
        if performative == FIPAMessage.Performative.PROPOSE and target == 1 and self_initiated_dialogue_label in self.dialogues:
            dialogue = self.dialogues[self_initiated_dialogue_label]
        elif performative == FIPAMessage.Performative.ACCEPT:
            if target == 2 and other_initiated_dialogue_label in self.dialogues:
                dialogue = self.dialogues[other_initiated_dialogue_label]
            elif target == 3 and self_initiated_dialogue_label in self.dialogues:
                dialogue = self.dialogues[self_initiated_dialogue_label]
            else:
                raise ValueError('Should have found dialogue.')
        elif performative == FIPAMessage.Performative.DECLINE:
            if target == 1 and self_initiated_dialogue_label in self.dialogues:
                dialogue = self.dialogues[self_initiated_dialogue_label]
            elif target == 2 and other_initiated_dialogue_label in self.dialogues:
                dialogue = self.dialogues[other_initiated_dialogue_label]
            elif target == 3 and self_initiated_dialogue_label in self.dialogues:
                dialogue = self.dialogues[self_initiated_dialogue_label]
            else:
                raise ValueError('Should have found dialogue.')
        else:
            raise ValueError('Should have found dialogue.')
        return dialogue

    def _next_dialogue_id(self) -> int:
        """
        Increment the id and returns it.

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

        :return: the created dialogue
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

        :return: the created dialogue
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

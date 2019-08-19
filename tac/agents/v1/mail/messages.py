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

"""Protocol module v2."""
from abc import abstractmethod
from copy import copy
from enum import Enum
from typing import Optional, Any, Union, Dict

from oef.messages import OEFErrorOperation
from oef.query import Query
from oef.schema import Description

# from tac.agents.v1.base.dialogues import DialogueLabel
DialogueLabel = int

Address = str
ProtocolId = str


class Message:

    protocol_id = "default"

    def __init__(self, body: Optional[Dict] = None,
                 **kwargs):
        """
        Initialize a Message object.

        :param body: the dictionary of values to hold.
        """
        self._body = copy(body) if body else {}  # type: Dict[str, Any]
        self._body.update(kwargs)

    @property
    def body(self) -> Dict:
        """
        The body of the message (in dictionary form)
        :return: the body
        """
        return self._body

    @body.setter
    def body(self, body: Dict):
        """

        :param body:
        :return:
        """
        self._body = body

    def set(self, key: str, value: Any) -> None:
        """
        Set key and value pair.

        :param key: the key.
        :param value: the value.
        :return: None
        """
        self._body[key] = value

    def get(self, key: str) -> Optional[Any]:
        """Get value for key."""
        return self._body.get(key, None)

    def unset(self, key: str) -> None:
        """Unset valye for key."""
        self._body.pop(key, None)

    def is_set(self, key: str) -> bool:
        """Check value is set for key."""
        return key in self._body

    def check_consistency(self) -> bool:
        """Check that the data is consistent."""
        return True

    def __eq__(self, other):
        return isinstance(other, Message) \
            and self.body == other.body


class OEFMessage(Message):
    """The OEF message class."""

    protocol_id = "oef"

    class Type(Enum):
        """OEF Message types."""

        REGISTER_SERVICE = "register_service"
        REGISTER_AGENT = "register_agent"
        UNREGISTER_SERVICE = "unregister_service"
        UNREGISTER_AGENT = "unregister_agent"
        SEARCH_SERVICES = "search_services"
        SEARCH_AGENTS = "search_agents"
        OEF_ERROR = "oef_error"
        DIALOGUE_ERROR = "dialogue_error"
        SEARCH_RESULT = "search_result"

    def __init__(self, to: Optional[Address] = None,
                 sender: Optional[Address] = None,
                 oef_type: Optional[Type] = None,
                 **body):
        """
        Initialize.

        :param to: the public key of the receiver.
        :param sender: the public key of the sender.
        :param protocol_id: the protocol id.
        """
        super().__init__(to=to, sender=sender, protocol_id=self.protocol_id, type=oef_type, **body)

    def check_consistency(self) -> bool:
        """Check that the data is consistent."""
        try:
            assert self.is_set("type")
            oef_type = OEFMessage.Type(self.get("type"))
            if oef_type == OEFMessage.Type.REGISTER_SERVICE:
                service_description = self.get("service_description")
                assert self.is_set("id")
                assert self.is_set("service_id")
                service_id = self.get("service_id")
                assert isinstance(service_description, Description)
                assert isinstance(service_id, str)
            elif oef_type == OEFMessage.Type.REGISTER_AGENT:
                assert self.is_set("id")
                assert self.is_set("agent_description")
                agent_description = self.get("agent_description")
                assert isinstance(agent_description, Description)
            elif oef_type == OEFMessage.Type.UNREGISTER_SERVICE:
                assert self.is_set("id")
                assert self.is_set("service_id")
                service_id = self.get("service_id")
                assert isinstance(service_id, str)
            elif oef_type == OEFMessage.Type.UNREGISTER_AGENT:
                assert self.is_set("id")
            elif oef_type == OEFMessage.Type.SEARCH_SERVICES:
                assert self.is_set("id")
                assert self.is_set("query")
                query = self.get("query")
                assert isinstance(query, Query)
            elif oef_type == OEFMessage.Type.SEARCH_AGENTS:
                assert self.is_set("id")
                assert self.is_set("query")
                query = self.get("query")
                assert isinstance(query, Query)
            elif oef_type == OEFMessage.Type.SEARCH_RESULT:
                assert self.is_set("id")
                assert self.is_set("agents")
                agents = self.get("agents")
                assert type(agents) == list and all(type(a) == str for a in agents)
            elif oef_type == OEFMessage.Type.OEF_ERROR:
                assert self.is_set("id")
                assert self.is_set("operation")
                operation = self.get("operation")
                assert operation in set(OEFErrorOperation)
            elif oef_type == OEFMessage.Type.DIALOGUE_ERROR:
                assert self.is_set("id")
                assert self.is_set("dialogue_id")
                assert self.is_set("origin")
            else:
                raise ValueError("Type not recognized.")
        except (AssertionError, ValueError):
            return False

        return True


class ByteMessage(Message):
    """The Byte message class."""

    protocol_id = "bytes"

    def __init__(self, message_id: Optional[int] = None,
                 dialogue_id: Optional[int] = None,
                 content: bytes = b""):
        """
        Initialize.

        :param message_id: the message id.
        :param dialogue_id: the dialogue id.
        :param content: the message content.
        """
        super().__init__(id=message_id, dialogue_id=dialogue_id, content=content)


class SimpleMessage(Message):
    """The Simple message class."""

    protocol_id = "simple"

    class Type(Enum):
        """Simple message types."""

        BYTES = "bytes"
        ERROR = "error"

    def __init__(self, type: Optional[Type] = None,
                 **kwargs):
        """
        Initialize.

        :param type: the type.
        """
        super().__init__(type=type, **kwargs)


class FIPAMessage(Message):
    """The FIPA message class."""

    protocol_id = "fipa"

    class Performative(Enum):
        """FIPA performatives."""

        CFP = "cfp"
        PROPOSE = "propose"
        ACCEPT = "accept"
        MATCH_ACCEPT = "match_accept"
        DECLINE = "decline"

    def __init__(self, message_id: Optional[int] = None,
                 dialogue_id: Optional[DialogueLabel] = None,
                 target: Optional[int] = None,
                 performative: Optional[Union[str, Performative]] = None,
                 **kwargs):
        """
        Initialize.

        :param message_id: the message id.
        :param dialogue_id: the dialogue id.
        :param target: the message target.
        :param performative: the message performative.
        """
        super().__init__(id=message_id,
                         dialogue_id=dialogue_id,
                         target=target,
                         performative=FIPAMessage.Performative(performative),
                         **kwargs)

    def check_consistency(self) -> bool:
        """Check that the data is consistent."""
        try:
            assert self.is_set("target")
            performative = FIPAMessage.Performative(self.get("performative"))
            if performative == FIPAMessage.Performative.CFP:
                query = self.get("query")
                assert isinstance(query, Query) or isinstance(query, bytes) or query is None
            elif performative == FIPAMessage.Performative.PROPOSE:
                proposal = self.get("proposal")
                assert type(proposal) == list and all(isinstance(d, Description) or type(d) == bytes for d in proposal)
            elif performative == FIPAMessage.Performative.ACCEPT \
                    or performative == FIPAMessage.Performative.MATCH_ACCEPT \
                    or performative == FIPAMessage.Performative.DECLINE:
                pass
            else:
                raise ValueError("Performative not recognized.")

        except (AssertionError, ValueError, KeyError):
            return False

        return True

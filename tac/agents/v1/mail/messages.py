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
from copy import deepcopy
from enum import Enum
from typing import Optional, Dict, Any, Union

from oef.messages import OEFErrorOperation
from oef.query import Query
from oef.schema import Description

# from tac.agents.v1.base.dialogues import DialogueLabel
DialogueLabel = int

Address = str
ProtocolId = str


class Message:

    def __init__(self, to: Optional[Address] = None,
                 sender: Optional[Address] = None,
                 protocol_id: Optional[ProtocolId] = None,
                 **body):
        self._to = to
        self._sender = sender
        self._protocol_id = protocol_id
        self._body = deepcopy(body) if body else {}

    @property
    def to(self) -> Address:
        return self._to

    @to.setter
    def to(self, to: Address):
        self._to = to

    @property
    def sender(self) -> Address:
        return self._sender

    @sender.setter
    def sender(self, sender: Address):
        self._sender = sender

    @property
    def protocol_id(self) -> Optional[ProtocolId]:
        return self._protocol_id

    def set(self, key: str, value: Any) -> None:
        self._body[key] = value

    def get(self, key: str) -> Optional[Any]:
        return self._body.get(key, None)

    def unset(self, key: str) -> None:
        self._body.pop(key, None)

    def is_set(self, key: str) -> bool:
        return key in self._body

    def check_consistency(self) -> bool:
        """Check that the data are consistent."""
        return True


class OEFMessage(Message):

    protocol_id = "oef"

    class Type(Enum):
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
        super().__init__(to=to, sender=sender, protocol_id=self.protocol_id, type=oef_type, **body)

    def check_consistency(self) -> bool:
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

    protocol_id = "bytes"

    def __init__(self, to: Optional[Address] = None,
                 sender: Optional[Address] = None,
                 message_id: Optional[int] = None,
                 dialogue_id: Optional[int] = None,
                 content: bytes = b""):
        super().__init__(to=to, sender=sender, id=message_id, dialogue_id=dialogue_id, content=content)


class SimpleByteMessage(Message):

    protocol_id = "default"

    def __init__(self, to: Optional[Address] = None,
                 sender: Optional[Address] = None,
                 content: bytes = b""):
        super().__init__(to=to, sender=sender, protocol_id=self.protocol_id, content=content)


class FIPAMessage(Message):

    protocol_id = "fipa"

    class Performative(Enum):
        CFP = "cfp"
        PROPOSE = "propose"
        ACCEPT = "accept"
        MATCH_ACCEPT = "match_accept"
        DECLINE = "decline"

    def __init__(self, to: Optional[Address] = None,
                 sender: Optional[Address] = None,
                 msg_id: Optional[int] = None,
                 dialogue_id: Optional[DialogueLabel] = None,
                 target: Optional[int] = None,
                 performative: Optional[Union[str, Performative]] = None,
                 **body):
        super().__init__(to,
                         sender,
                         protocol_id=self.protocol_id,
                         id=msg_id,
                         dialogue_id=dialogue_id,
                         target=target,
                         performative=FIPAMessage.Performative(performative),
                         **body)

    def check_consistency(self) -> bool:
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

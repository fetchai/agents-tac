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
from typing import Optional, Dict, Any

from oef.query import Query
from oef.schema import Description

from tac.agents.v1.base.dialogues import DialogueLabel

Address = str
ProtocolId = str


class Message:

    def __init__(self, to: Address,
                 sender: Address,
                 body: Optional[Dict[str, Any]] = None,
                 protocol_id: Optional[ProtocolId] = None):
        self._to = to
        self._sender = sender
        self._body = deepcopy(body) if body else {}
        self._protocol_id = protocol_id

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

        SEARCH_RESULT = "search_result"

    def __init__(self, to: Address,
                 sender: Address,
                 message_id: int,
                 oef_type: Type,
                 body: Dict[str, Any]):
        _body = dict(**body)
        _body["type"] = oef_type
        _body["id"] = message_id
        super().__init__(to, sender, body=body, protocol_id=self.protocol_id)

    def check_consistency(self) -> bool:
        try:
            assert self.is_set("id")
            assert self.is_set("type")
            oef_type = OEFMessage.Type(self.get("type"))
            if oef_type == OEFMessage.Type.REGISTER_SERVICE:
                service_description = self.get("service_description")
                service_id = self.get("service_id")
                assert isinstance(service_description, Description)
                assert isinstance(service_id, str)
            elif oef_type == OEFMessage.Type.REGISTER_AGENT:
                agent_description = self.get("agent_description")
                assert isinstance(agent_description, Description)
            elif oef_type == OEFMessage.Type.UNREGISTER_SERVICE:
                service_id = self.get("service_id")
                assert isinstance(service_id, str)
            elif oef_type == OEFMessage.Type.UNREGISTER_AGENT:
                pass
            elif oef_type == OEFMessage.Type.SEARCH_SERVICES:
                query = self.get("query")
                assert isinstance(query, Query)
            elif oef_type == OEFMessage.Type.SEARCH_AGENTS:
                query = self.get("query")
                assert isinstance(query, Query)
            elif oef_type == OEFMessage.Type.SEARCH_RESULT:
                agents = self.get("agents")
                assert type(agents) == list and all(type(a) == str for a in agents)
            else:
                raise ValueError("Type not recognized.")
        except (AssertionError, ValueError):
            return False

        return True


class ByteMessage(Message):

    protocol_id = "bytes"

    def __init__(self, to: Address,
                 sender: Address,
                 dialogue_id: DialogueLabel,
                 content: bytes = b""):
        body = dict(dialogue_id=dialogue_id, content=content)
        super().__init__(to, sender, body=body, protocol_id=self.protocol_id)


class FIPAMessage(Message):

    protocol_id = "fipa"

    class Type(Enum):
        CFP = "cfp"
        PROPOSE = "propose"
        ACCEPT = "accept"
        DECLINE = "decline"

    def __init__(self, to: Address,
                 sender: Address,
                 dialogue_id: DialogueLabel,
                 target: int,
                 performative: Type,
                 body: Dict[str, Any]):
        _body = dict(**body)
        _body["dialogue_id"] = dialogue_id
        _body["target"] = target
        _body["performative"] = performative
        super().__init__(to, sender, body=_body, protocol_id=self.protocol_id)

    def check_consistency(self) -> bool:
        try:
            assert self.is_set("target")
            performative = FIPAMessage.Type(self.get("performative"))
            if performative == FIPAMessage.Type.CFP:
                query = self.get("query")
                assert isinstance(query, Query) or query is None
            elif performative == FIPAMessage.Type.PROPOSE:
                proposal = self.get("proposal")
                assert type(proposal) == list and all(isinstance(d, Description) for d in proposal)
            elif performative == FIPAMessage.Type.ACCEPT or performative == FIPAMessage.Type.DECLINE:
                pass
            else:
                raise ValueError("Performative not recognized.")

        except (AssertionError, ValueError, KeyError):
            return False

        return True

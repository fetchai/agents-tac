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
from abc import ABC
from typing import List

from oef.messages import CFP_TYPES, PROPOSE_TYPES, OEFErrorOperation
from oef.query import Query
from oef.schema import Description

from tac.agents.v1.mail.base import Message

RequestId = int
SearchId = int
MessageId = int
DialogueId = int
AgentAddress = str


class OEFMessage(Message, ABC):
    pass


class OEFRequest(OEFMessage, ABC):
    pass


class OEFResponse(OEFMessage, ABC):
    pass


class OEFError(OEFResponse, ABC):
    pass


class OEFGenericError(OEFError):

    def __init__(self, answer_id: RequestId, operation: OEFErrorOperation):
        super().__init__()
        self.answer_id = answer_id
        self.operation = operation


class OEFDialogueError(OEFError):

    def __init__(self, answer_id: MessageId, dialogue_id: DialogueId, origin: AgentAddress):
        super().__init__()
        self.answer_id = answer_id
        self.dialogue_id = dialogue_id
        self.origin = origin


class OEFRegisterServiceRequest(OEFRequest):

    def __init__(self, msg_id: RequestId, agent_description: Description, service_id: str = ""):
        super().__init__()
        self.msg_id = msg_id
        self.agent_description = agent_description
        self.service_id = service_id


class OEFUnregisterServiceRequest(OEFRequest):

    def __init__(self, msg_id: RequestId, agent_description: Description, service_id: str = ""):
        super().__init__()
        self.msg_id = msg_id
        self.agent_description = agent_description
        self.service_id = service_id


class OEFRegisterAgentRequest(OEFRequest):

    def __init__(self, msg_id: RequestId, agent_description: Description):
        self.msg_id = msg_id
        self.agent_description = agent_description


class OEFUnregisterAgentRequest(OEFRequest):

    def __init__(self, msg_id: RequestId):
        self.msg_id = msg_id


class OEFSearchRequest(OEFRequest):
    pass


class OEFSearchServicesRequest(OEFSearchRequest):

    def __init__(self, search_id: SearchId, query: Query):
        super().__init__()
        self.search_id = search_id
        self.query = query


class OEFSearchAgentsRequest(OEFSearchRequest):

    def __init__(self, search_id: SearchId, query: Query):
        super().__init__()
        self.search_id = search_id
        self.query = query


class OEFSearchResult(OEFResponse):

    def __init__(self, search_id: SearchId, agents: List[str]):
        super().__init__()
        self.search_id = search_id
        self.agents = agents


class OEFAgentMessage(OEFMessage):

    def __init__(self, msg_id: MessageId, dialogue_id: DialogueId, destination: AgentAddress):
        super().__init__()
        self.msg_id = msg_id
        self.dialogue_id = dialogue_id
        self.destination = destination


class OEFAgentByteMessage(OEFAgentMessage):

    def __init__(self, msg_id: MessageId, dialogue_id: DialogueId, destination: AgentAddress, content: bytes):
        super().__init__(msg_id, dialogue_id, destination)
        self.content = content


class OEFAgentFIPAMessage(OEFAgentMessage):

    def __init__(self, msg_id: MessageId, dialogue_id: DialogueId, destination: AgentAddress, target: MessageId):
        super().__init__(msg_id, dialogue_id, destination)
        self.target = target


class OEFAgentCfp(OEFAgentFIPAMessage):

    def __init__(self, msg_id: MessageId, dialogue_id: DialogueId, destination: AgentAddress, target: MessageId, query: CFP_TYPES):
        super().__init__(msg_id, dialogue_id, destination, target)
        self.query = query


class OEFAgentPropose(OEFAgentFIPAMessage):

    def __init__(self, msg_id: MessageId, dialogue_id: DialogueId, destination: AgentAddress, target: MessageId, proposal: PROPOSE_TYPES):
        super().__init__(msg_id, dialogue_id, destination, target)
        self.proposal = proposal


class OEFAgentAccept(OEFAgentFIPAMessage):
    pass


class OEFAgentDecline(OEFAgentFIPAMessage):
    pass

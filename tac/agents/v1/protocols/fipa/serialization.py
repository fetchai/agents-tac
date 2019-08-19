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

"""Serialization for the FIPA protocol."""
import base58
from google.protobuf.struct_pb2 import Struct
from oef.schema import Description

from tac.agents.v1.mail.messages import FIPAMessage, Message
from tac.agents.v1.mail.protocol import Serializer, Envelope
from tac.agents.v1.protocols import base_pb2
from tac.agents.v1.protocols.fipa import fipa_pb2


class FIPASerializer(Serializer):
    
    def encode(self, msg: Message) -> bytes:

        fipa_msg = fipa_pb2.FIPAMessage()
        fipa_msg.message_id = msg.get("id")
        fipa_msg.dialogue_id = msg.get("dialogue_id")
        fipa_msg.target = msg.get("target")

        performative_id = msg.get("performative").value
        if performative_id == "cfp":
            performative = fipa_pb2.FIPAMessage.CFP()
            performative.query.update(msg.get("query"))
            fipa_msg.cfp.CopyFrom(performative)
        elif performative_id == "propose":
            performative = fipa_pb2.FIPAMessage.Propose()
            proposal = msg.get("proposal")
            for p in proposal:
                p: Description
                new_struct = performative.proposal.add()
                new_struct.update(p.values)

            for bytes_p in performative.proposal:
                print(bytes_p)

            fipa_msg.propose.CopyFrom(performative)

        elif performative_id == "accept":
            performative = fipa_pb2.FIPAMessage.Accept()
            fipa_msg.accept.CopyFrom(performative)
        elif performative_id == "match_accept":
            performative = fipa_pb2.FIPAMessage.MatchAccept()
            fipa_msg.match_accept.CopyFrom(performative)
        elif performative_id == "decline":
            performative = fipa_pb2.FIPAMessage.Decline()
            fipa_msg.decline.CopyFrom(performative)
        else:
            raise ValueError("Performative not valid: {}".format(performative_id))

        fipa_bytes = fipa_msg.SerializeToString()
        return fipa_bytes

    def decode(self, obj: bytes) -> Message:
        fipa_pb = fipa_pb2.FIPAMessage()
        fipa_pb.ParseFromString(obj)
        message_id = fipa_pb.message_id
        dialogue_id = fipa_pb.dialogue_id
        target = fipa_pb.target

        performative = fipa_pb.WhichOneof("performative")
        performative_content = dict()
        if performative == "cfp":
            query = dict(fipa_pb.cfp.query)
            performative_content["query"] = query
        elif performative == "propose":
            proposal = [dict(p) for p in fipa_pb.propose.proposal]
            performative_content["proposal"] = proposal
        elif performative == "accept":
            pass
        elif performative == "match_accept":
            pass
        elif performative == "decline":
            pass
        else:
            raise ValueError("Performative not valid.")

        return FIPAMessage(message_id=message_id, dialogue_id=dialogue_id, target=target,
                           performative=performative, **performative_content)

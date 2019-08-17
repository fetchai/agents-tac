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

"""Serialization module for the default protocol."""
import json

import base58

from tac.agents.v1.mail.messages import Message, SimpleMessage
from tac.agents.v1.mail.protocol import Serializer


class SimpleSerializer(Serializer):
    """Serializer for the 'simple' protocol."""

    def encode(self, msg: Message) -> bytes:
        assert msg.protocol_id == SimpleMessage.protocol_id

        body = {}

        msg_type = msg.get("type")
        assert msg_type in set(SimpleMessage.Type)
        body["type"] = str(msg_type.value)

        if msg_type == SimpleMessage.Type.BYTES:
            body["content"] = base58.b58encode(msg.get("content")).decode("utf-8")
        elif msg_type == SimpleMessage.Type.ERROR:
            body["error_code"] = msg.get("error_code")
            body["error_msg"] = msg.get("error_msg")
        else:
            raise ValueError("Type not recognized.")

        json_msg = {
            "to": msg.to,
            "sender": msg.sender,
            "protocol_id": msg.protocol_id,
            "body": body
        }

        bytes_msg = json.dumps(json_msg).encode("utf-8")
        return bytes_msg

    def decode(self, obj: bytes) -> Message:
        json_msg = json.loads(obj.decode("utf-8"))

        to = json_msg["to"]
        sender = json_msg["sender"]
        protocol_id = json_msg["protocol_id"]
        body = {}

        json_body = json_msg["body"]
        msg_type = SimpleMessage.Type(json_body["type"])
        if msg_type == SimpleMessage.Type.BYTES:
            content = base58.b58decode(json_body["content"].encode("utf-8"))
            body["content"] = content
        elif msg_type == SimpleMessage.Type.ERROR:
            body["error_code"] = json_body["error_code"]
            body["error_msg"] = json_body["error_msg"]
        else:
            raise ValueError("Type not recognized.")

        return Message(to=to, sender=sender, protocol_id=protocol_id, body=body)

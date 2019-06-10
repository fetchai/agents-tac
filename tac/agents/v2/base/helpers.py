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
from typing import Union

from oef.messages import Message as SimpleMessage, SearchResult, OEFErrorMessage, DialogueErrorMessage

from tac.helpers.crypto import Crypto
from tac.platform.protocol import Response

OEFMessage = Union[SearchResult, OEFErrorMessage, DialogueErrorMessage]
Message = Union[OEFMessage]


def is_oef_message(msg: Message) -> bool:
    msg_type = type(msg)
    return msg_type in {SearchResult, OEFErrorMessage, DialogueErrorMessage}


def is_controller_message(msg: Message, crypto: Crypto) -> bool:
    if not isinstance(msg, SimpleMessage):
        return False

    try:
        msg: SimpleMessage
        byte_content = msg.msg
        sender_pbk = msg.destination  # now the origin is the destination!
        Response.from_pb(byte_content, sender_pbk, crypto)
    except Exception:
        return False

    return True

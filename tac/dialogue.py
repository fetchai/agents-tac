#!/usr/bin/env python3
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

"""Module that contains utilities for keeping information about negotiations.
TODO: discuss whether to integrate with the dialogue agent.
"""

import logging
from typing import Optional

from oef.dialogue import SingleDialogue, DialogueAgent
from oef.messages import PROPOSE_TYPES, CFP_TYPES

logger = logging.getLogger(__name__)


class BaselineDialogue(SingleDialogue):

    def __init__(self, agent: DialogueAgent,
                 destination: str,
                 id_: Optional[int] = None):
        super().__init__(agent, destination, id_=id_)

    def on_message(self, msg_id: int, content: bytes) -> None:
        pass

    def on_cfp(self, msg_id: int, target: int, query: CFP_TYPES) -> None:
        pass

    def on_propose(self, msg_id: int, target: int, proposal: PROPOSE_TYPES) -> None:
        pass

    def on_accept(self, msg_id: int, target: int) -> None:
        pass

    def on_decline(self, msg_id: int, target: int) -> None:
        pass

    def on_dialogue_error(self, answer_id: int, dialogue_id: int, origin: str) -> None:
        pass

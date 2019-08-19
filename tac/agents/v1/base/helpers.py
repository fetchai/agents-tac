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

"""This module contains helper methods for base agent implementations."""
import logging

from tac.agents.v1.base.dialogues import DialogueLabel
from tac.agents.v1.mail.messages import OEFMessage, FIPAMessage
from tac.agents.v1.mail.protocol import Envelope
from tac.helpers.crypto import Crypto
from tac.platform.protocol import Response


logger = logging.getLogger(__name__)


def is_oef_message(msg: Envelope) -> bool:
    """
    Check whether a message is from the oef.

    :param msg: the message
    :return: boolean indicating whether or not the message is from the oef
    """
    return msg.protocol_id == "oef" and msg.message.get("type") in set(OEFMessage.Type)


def is_controller_message(msg: Envelope, crypto: Crypto) -> bool:
    """
    Check whether a message is from the controller.

    :param msg: the message
    :param crypto: the crypto of the agent
    :return: boolean indicating whether or not the message is from the controller
    """
    if not msg.protocol_id == "bytes":
        return False

    try:
        byte_content = msg.message.get("content")
        sender_pbk = msg.sender
        Response.from_pb(byte_content, sender_pbk, crypto)
    except Exception as e:
        logger.debug("Not a Controller message: {}".format(str(e)))
        # try:
        #     byte_content = msg.get("content")
        #     sender_pbk = msg.sender
        #     Response.from_pb(byte_content, sender_pbk, crypto)
        # except:
        #     pass
        return False

    return True


def is_fipa_message(msg: Envelope) -> bool:
    """Chcek whether a message is a FIPA message."""
    return msg.protocol_id == "fipa" and msg.message.get("performative") in set(FIPAMessage.Performative)


def generate_transaction_id(agent_pbk: str, opponent_pbk: str, dialogue_label: DialogueLabel, agent_is_seller: bool) -> str:
    """
    Make a transaction id.

    :param agent_pbk: the pbk of the agent.
    :param opponent_pbk: the public key of the opponent.
    :param dialogue_label: the dialogue label
    :param agent_is_seller: boolean indicating if the agent is a seller
    :return: a transaction id
    """
    # the format is {buyer_pbk}_{seller_pbk}_{dialogue_id}_{dialogue_starter_pbk}
    assert opponent_pbk == dialogue_label.dialogue_opponent_pbk
    buyer_pbk, seller_pbk = (opponent_pbk, agent_pbk) if agent_is_seller else (agent_pbk, opponent_pbk)
    transaction_id = "{}_{}_{}_{}".format(buyer_pbk, seller_pbk, dialogue_label.dialogue_id, dialogue_label.dialogue_starter_pbk)
    return transaction_id


def dialogue_label_from_transaction_id(agent_pbk: str, transaction_id: str) -> DialogueLabel:
    """
    Recover dialogue label from transaction id.

    :param agent_pbk: the pbk of the agent.
    :param transaction_id: the transaction id
    :return: a dialogue label
    """
    buyer_pbk, seller_pbk, dialogue_id, dialogue_starter_pbk = transaction_id.split('_')
    if agent_pbk == buyer_pbk:
        dialogue_opponent_pbk = seller_pbk
    else:
        dialogue_opponent_pbk = buyer_pbk
    dialogue_label = DialogueLabel(int(dialogue_id), dialogue_opponent_pbk, dialogue_starter_pbk)
    return dialogue_label

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

"""This module contains a class which implements the FIPA protocol for the TAC."""

import json
import logging
import pprint
from typing import List

from tac.aea.crypto.base import Crypto
from tac.aea.mail.messages import FIPAMessage, Message, DefaultMessage
from tac.aea.mail.protocol import Envelope
from tac.aea.protocols.default.serialization import DefaultSerializer
from tac.aea.protocols.fipa.serialization import FIPASerializer
from tac.agents.participant.base.dialogues import Dialogue
from tac.agents.participant.base.game_instance import GameInstance
from tac.agents.participant.base.helpers import generate_transaction_id
from tac.agents.participant.base.stats_manager import EndState
from tac.platform.protocol import Transaction

logger = logging.getLogger(__name__)

STARTING_MESSAGE_ID = 1


class FIPABehaviour:
    """Specifies FIPA negotiation behaviours."""

    def __init__(self, crypto: Crypto, game_instance: GameInstance, agent_name: str) -> None:
        """
        Instantiate the FIPABehaviour.

        :param crypto: the crypto module
        :param game_instance: the game instance
        :param agent_name: the agent_name of the agent

        :return: None
        """
        self._crypto = crypto
        self._game_instance = game_instance
        self._agent_name = agent_name

    @property
    def game_instance(self) -> GameInstance:
        """Get the game instance."""
        return self._game_instance

    @property
    def crypto(self) -> Crypto:
        """Get the crypto."""
        return self._crypto

    @property
    def agent_name(self) -> str:
        """Get the agent name."""
        return self._agent_name

    def on_cfp(self, cfp: Message, dialogue: Dialogue) -> Envelope:
        """
        Handle a CFP.

        :param cfp: the message containing the CFP
        :param dialogue: the dialogue

        :return: a Propose or a Decline
        """
        assert cfp.get("performative") == FIPAMessage.Performative.CFP
        goods_description = self.game_instance.get_service_description(is_supply=dialogue.is_seller)
        new_msg_id = cfp.get("id") + 1
        decline = False
        cfp_services = json.loads(cfp.get("query").decode('utf-8'))
        if not self.game_instance.is_matching(cfp_services, goods_description):
            decline = True
            logger.debug("[{}]: Current holdings do not satisfy CFP query.".format(self.agent_name))
        else:
            proposal = self.game_instance.generate_proposal(cfp_services, dialogue.is_seller)
            if proposal is None:
                decline = True
                logger.debug("[{}]: Current strategy does not generate proposal that satisfies CFP query.".format(self.agent_name))

        if decline:
            logger.debug("[{}]: sending to {} a Decline{}".format(self.agent_name, dialogue.dialogue_label.dialogue_opponent_pbk,
                                                                  pprint.pformat({
                                                                      "msg_id": new_msg_id,
                                                                      "dialogue_id": cfp.get("dialogue_id"),
                                                                      "origin": dialogue.dialogue_label.dialogue_opponent_pbk,
                                                                      "target": cfp.get("target")
                                                                  })))
            msg = FIPAMessage(message_id=new_msg_id, dialogue_id=cfp.get("dialogue_id"), performative=FIPAMessage.Performative.DECLINE, target=cfp.get("id"))
            dialogue.outgoing_extend([msg])
            msg_bytes = FIPASerializer().encode(msg)
            response = Envelope(to=dialogue.dialogue_label.dialogue_opponent_pbk, sender=self.crypto.public_key, protocol_id=FIPAMessage.protocol_id, message=msg_bytes)
            self.game_instance.stats_manager.add_dialogue_endstate(EndState.DECLINED_CFP, dialogue.is_self_initiated)
        else:
            transaction_id = generate_transaction_id(self.crypto.public_key, dialogue.dialogue_label.dialogue_opponent_pbk, dialogue.dialogue_label, dialogue.is_seller)
            transaction = Transaction.from_proposal(proposal=proposal,
                                                    transaction_id=transaction_id,
                                                    is_sender_buyer=not dialogue.is_seller,
                                                    counterparty=dialogue.dialogue_label.dialogue_opponent_pbk,
                                                    sender=self.crypto.public_key,
                                                    crypto=self.crypto)
            self.game_instance.transaction_manager.add_pending_proposal(dialogue.dialogue_label, new_msg_id, transaction)
            logger.debug("[{}]: sending to {} a Propose{}".format(self.agent_name, dialogue.dialogue_label.dialogue_opponent_pbk,
                                                                  pprint.pformat({
                                                                      "msg_id": new_msg_id,
                                                                      "dialogue_id": cfp.get("dialogue_id"),
                                                                      "origin": dialogue.dialogue_label.dialogue_opponent_pbk,
                                                                      "target": cfp.get("id"),
                                                                      "propose": proposal.values
                                                                  })))
            msg = FIPAMessage(performative=FIPAMessage.Performative.PROPOSE, message_id=new_msg_id, dialogue_id=cfp.get("dialogue_id"), target=cfp.get("id"), proposal=[proposal])
            dialogue.outgoing_extend([msg])
            dialogue.outgoing_extend([msg])
            msg_bytes = FIPASerializer().encode(msg)
            response = Envelope(to=dialogue.dialogue_label.dialogue_opponent_pbk, sender=self.crypto.public_key, protocol_id=FIPAMessage.protocol_id, message=msg_bytes)
        return response

    def on_propose(self, propose: Message, dialogue: Dialogue) -> Envelope:
        """
        Handle a Propose.

        :param propose: the message containing the Propose
        :param dialogue: the dialogue

        :return: an Accept or a Decline
        """
        logger.debug("[{}]: on propose as {}.".format(self.agent_name, dialogue.role))
        assert propose.get("performative") == FIPAMessage.Performative.PROPOSE
        proposal = propose.get("proposal")[0]
        transaction_id = generate_transaction_id(self.crypto.public_key, dialogue.dialogue_label.dialogue_opponent_pbk, dialogue.dialogue_label, dialogue.is_seller)
        transaction = Transaction.from_proposal(proposal=proposal,
                                                transaction_id=transaction_id,
                                                is_sender_buyer=not dialogue.is_seller,
                                                counterparty=dialogue.dialogue_label.dialogue_opponent_pbk,
                                                sender=self.crypto.public_key,
                                                crypto=self.crypto)
        new_msg_id = propose.get("id") + 1
        is_profitable_transaction, propose_log_msg = self.game_instance.is_profitable_transaction(transaction, dialogue)
        logger.debug(propose_log_msg)
        if is_profitable_transaction:
            logger.debug("[{}]: Accepting propose (as {}).".format(self.agent_name, dialogue.role))
            self.game_instance.transaction_manager.add_locked_tx(transaction, as_seller=dialogue.is_seller)
            self.game_instance.transaction_manager.add_pending_initial_acceptance(dialogue.dialogue_label, new_msg_id, transaction)
            msg = FIPAMessage(message_id=new_msg_id, dialogue_id=propose.get("dialogue_id"), target=propose.get("id"), performative=FIPAMessage.Performative.ACCEPT)
            dialogue.outgoing_extend([msg])
            msg_bytes = FIPASerializer().encode(msg)
            result = Envelope(to=dialogue.dialogue_label.dialogue_opponent_pbk, sender=self.crypto.public_key, protocol_id=FIPAMessage.protocol_id, message=msg_bytes)
        else:
            logger.debug("[{}]: Declining propose (as {})".format(self.agent_name, dialogue.role))
            msg = FIPAMessage(message_id=new_msg_id, dialogue_id=propose.get("dialogue_id"), target=propose.get("id"), performative=FIPAMessage.Performative.DECLINE)
            dialogue.outgoing_extend([msg])
            msg_bytes = FIPASerializer().encode(msg)
            result = Envelope(to=dialogue.dialogue_label.dialogue_opponent_pbk, sender=self.crypto.public_key, protocol_id=FIPAMessage.protocol_id, message=msg_bytes)
            self.game_instance.stats_manager.add_dialogue_endstate(EndState.DECLINED_PROPOSE, dialogue.is_self_initiated)
        return result

    def on_decline(self, decline: Message, dialogue: Dialogue) -> None:
        """
        Handle a Decline.

        :param decline: the message  containing the Decline
        :param dialogue: the dialogue

        :return: None
        """
        assert decline.get("performative") == FIPAMessage.Performative.DECLINE
        logger.debug("[{}]: on_decline: msg_id={}, dialogue_id={}, origin={}, target={}"
                     .format(self.agent_name, decline.get("id"), decline.get("dialogue_id"), dialogue.dialogue_label.dialogue_opponent_pbk, decline.get("target")))
        target = decline.get("target")
        if target == 1:
            self.game_instance.stats_manager.add_dialogue_endstate(EndState.DECLINED_CFP, dialogue.is_self_initiated)
        elif target == 2:
            self.game_instance.stats_manager.add_dialogue_endstate(EndState.DECLINED_PROPOSE, dialogue.is_self_initiated)
            transaction = self.game_instance.transaction_manager.pop_pending_proposal(dialogue.dialogue_label, target)
            if self.game_instance.strategy.is_world_modeling:
                self.game_instance.world_state.update_on_declined_propose(transaction)
        elif target == 3:
            self.game_instance.stats_manager.add_dialogue_endstate(EndState.DECLINED_ACCEPT, dialogue.is_self_initiated)
            transaction = self.game_instance.transaction_manager.pop_pending_initial_acceptance(dialogue.dialogue_label, target)
            self.game_instance.transaction_manager.pop_locked_tx(transaction.transaction_id)

        return None

    def on_accept(self, accept: Message, dialogue: Dialogue) -> List[Envelope]:
        """
        Handle an Accept.

        :param accept: the message containing the Accept
        :param dialogue: the dialogue
        :return: a Decline, or an Accept and a Transaction, or a Transaction (in a Message object)
        """
        assert accept.get("performative") == FIPAMessage.Performative.ACCEPT \
               and dialogue.dialogue_label in self.game_instance.transaction_manager.pending_proposals \
               and accept.get("target") in self.game_instance.transaction_manager.pending_proposals[dialogue.dialogue_label]
        logger.debug("[{}]: on_accept: msg_id={}, dialogue_id={}, origin={}, target={}"
                     .format(self.agent_name, accept.get("id"), accept.get("dialogue_id"), dialogue.dialogue_label.dialogue_opponent_pbk, accept.get("target")))
        new_msg_id = accept.get("id") + 1
        results = []
        transaction = self.game_instance.transaction_manager.pop_pending_proposal(dialogue.dialogue_label, accept.get("target"))
        is_profitable_transaction, accept_log_msg = self.game_instance.is_profitable_transaction(transaction, dialogue)
        logger.debug(accept_log_msg)
        if is_profitable_transaction:
            if self.game_instance.strategy.is_world_modeling:
                self.game_instance.world_state.update_on_initial_accept(transaction)
            logger.debug("[{}]: Locking the current state (as {}).".format(self.agent_name, dialogue.role))
            self.game_instance.transaction_manager.add_locked_tx(transaction, as_seller=dialogue.is_seller)

            msg = DefaultMessage(type=DefaultMessage.Type.BYTES, content=transaction.serialize())
            msg_bytes = DefaultSerializer().encode(msg)
            results.append(Envelope(to=self.game_instance.controller_pbk, sender=self.crypto.public_key, protocol_id=DefaultMessage.protocol_id, message=msg_bytes))
            dialogue.outgoing_extend([msg])

            msg = FIPAMessage(message_id=new_msg_id, dialogue_id=accept.get("dialogue_id"), target=accept.get("id"), performative=FIPAMessage.Performative.MATCH_ACCEPT)
            dialogue.outgoing_extend([msg])
            msg_bytes = FIPASerializer().encode(msg)
            results.append(Envelope(to=dialogue.dialogue_label.dialogue_opponent_pbk, sender=self.crypto.public_key, protocol_id=FIPAMessage.protocol_id, message=msg_bytes))
        else:
            logger.debug("[{}]: Decline the accept (as {}).".format(self.agent_name, dialogue.role))

            msg = FIPAMessage(message_id=new_msg_id, dialogue_id=accept.get("dialogue_id"), target=accept.get("id"), performative=FIPAMessage.Performative.DECLINE)
            dialogue.outgoing_extend([msg])
            msg_bytes = FIPASerializer().encode(msg)
            results.append(Envelope(to=dialogue.dialogue_label.dialogue_opponent_pbk, sender=self.crypto.public_key, protocol_id=FIPAMessage.protocol_id, message=msg_bytes))
            self.game_instance.stats_manager.add_dialogue_endstate(EndState.DECLINED_ACCEPT, dialogue.is_self_initiated)
        return results

    def on_match_accept(self, match_accept: Message, dialogue: Dialogue) -> List[Envelope]:
        """
        Handle a matching Accept.

        :param match_accept: the envelope containing the MatchAccept
        :param dialogue: the dialogue
        :return: a Transaction
        """
        assert match_accept.get("performative") == FIPAMessage.Performative.MATCH_ACCEPT \
               and dialogue.dialogue_label in self.game_instance.transaction_manager.pending_initial_acceptances \
               and match_accept.get("target") in self.game_instance.transaction_manager.pending_initial_acceptances[dialogue.dialogue_label]
        logger.debug("[{}]: on_match_accept: msg_id={}, dialogue_id={}, origin={}, target={}"
                     .format(self.agent_name, match_accept.get("id"), match_accept.get("dialogue_id"), dialogue.dialogue_label.dialogue_opponent_pbk, match_accept.get("target")))
        results = []
        transaction = self.game_instance.transaction_manager.pop_pending_initial_acceptance(dialogue.dialogue_label, match_accept.get("target"))
        msg = DefaultMessage(type=DefaultMessage.Type.BYTES, content=transaction.serialize())
        msg_bytes = DefaultSerializer().encode(msg)
        results.append(Envelope(to=self.game_instance.controller_pbk, sender=self.crypto.public_key, protocol_id=DefaultMessage.protocol_id, message=msg_bytes))
        dialogue.outgoing_extend([msg])
        return results

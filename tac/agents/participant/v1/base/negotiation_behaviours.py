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
from tac.aea.mail.messages import FIPAMessage, ByteMessage
from tac.aea.mail.protocol import Envelope
from tac.agents.participant.v1.base.dialogues import Dialogue
from tac.agents.participant.v1.base.game_instance import GameInstance
from tac.agents.participant.v1.base.helpers import generate_transaction_id
from tac.agents.participant.v1.base.stats_manager import EndState
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

    def on_cfp(self, envelope: Envelope, dialogue: Dialogue) -> Envelope:
        """
        Handle a CFP.

        :param envelope: the envelope containing the CFP
        :param dialogue: the dialogue

        :return: a Propose or a Decline
        """
        cfp = envelope.message
        assert cfp.protocol_id == "fipa" and cfp.get("performative") == FIPAMessage.Performative.CFP
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
            logger.debug("[{}]: sending to {} a Decline{}".format(self.agent_name, envelope.sender,
                                                                  pprint.pformat({
                                                                      "msg_id": new_msg_id,
                                                                      "dialogue_id": cfp.get("dialogue_id"),
                                                                      "origin": envelope.sender,
                                                                      "target": cfp.get("target")
                                                                  })))
            response = Envelope(to=envelope.sender, sender=self.crypto.public_key, protocol_id=FIPAMessage.protocol_id,
                                message=FIPAMessage(message_id=new_msg_id, dialogue_id=cfp.get("dialogue_id"), performative=FIPAMessage.Performative.DECLINE, target=cfp.get("id")))
            self.game_instance.stats_manager.add_dialogue_endstate(EndState.DECLINED_CFP, dialogue.is_self_initiated)
        else:
            transaction_id = generate_transaction_id(self.crypto.public_key, envelope.sender, dialogue.dialogue_label, dialogue.is_seller)
            transaction = Transaction.from_proposal(proposal=proposal,
                                                    transaction_id=transaction_id,
                                                    is_sender_buyer=not dialogue.is_seller,
                                                    counterparty=envelope.sender,
                                                    sender=self.crypto.public_key,
                                                    crypto=self.crypto)
            self.game_instance.transaction_manager.add_pending_proposal(dialogue.dialogue_label, new_msg_id, transaction)
            logger.debug("[{}]: sending to {} a Propose{}".format(self.agent_name, envelope.sender,
                                                                  pprint.pformat({
                                                                      "msg_id": new_msg_id,
                                                                      "dialogue_id": cfp.get("dialogue_id"),
                                                                      "origin": envelope.sender,
                                                                      "target": cfp.get("id"),
                                                                      "propose": proposal.values
                                                                  })))
            response = Envelope(to=envelope.sender, sender=self.crypto.public_key, protocol_id=FIPAMessage.protocol_id,
                                message=FIPAMessage(performative=FIPAMessage.Performative.PROPOSE, message_id=new_msg_id, dialogue_id=cfp.get("dialogue_id"), target=cfp.get("id"), proposal=[proposal]))
        return response

    def on_propose(self, envelope: Envelope, dialogue: Dialogue) -> Envelope:
        """
        Handle a Propose.

        :param envelope: the envelope containing the Propose
        :param dialogue: the dialogue

        :return: an Accept or a Decline
        """
        propose = envelope.message
        logger.debug("[{}]: on propose as {}.".format(self.agent_name, dialogue.role))
        assert propose.protocol_id == "fipa" and propose.get("performative") == FIPAMessage.Performative.PROPOSE
        proposal = propose.get("proposal")[0]
        transaction_id = generate_transaction_id(self.crypto.public_key, envelope.sender, dialogue.dialogue_label, dialogue.is_seller)
        transaction = Transaction.from_proposal(proposal=proposal,
                                                transaction_id=transaction_id,
                                                is_sender_buyer=not dialogue.is_seller,
                                                counterparty=envelope.sender,
                                                sender=self.crypto.public_key,
                                                crypto=self.crypto)
        new_msg_id = propose.get("id") + 1
        is_profitable_transaction, message = self.game_instance.is_profitable_transaction(transaction, dialogue)
        logger.debug(message)
        if is_profitable_transaction:
            logger.debug("[{}]: Accepting propose (as {}).".format(self.agent_name, dialogue.role))
            self.game_instance.transaction_manager.add_locked_tx(transaction, as_seller=dialogue.is_seller)
            self.game_instance.transaction_manager.add_pending_initial_acceptance(dialogue.dialogue_label, new_msg_id, transaction)
            result = Envelope(to=envelope.sender, sender=self.crypto.public_key, protocol_id=FIPAMessage.protocol_id,
                              message=FIPAMessage(message_id=new_msg_id, dialogue_id=propose.get("dialogue_id"), target=propose.get("id"), performative=FIPAMessage.Performative.ACCEPT))
        else:
            logger.debug("[{}]: Declining propose (as {})".format(self.agent_name, dialogue.role))
            result = Envelope(to=envelope.sender, sender=self.crypto.public_key, protocol_id=FIPAMessage.protocol_id,
                              message=FIPAMessage(message_id=new_msg_id, dialogue_id=propose.get("dialogue_id"), target=propose.get("id"), performative=FIPAMessage.Performative.DECLINE))
            self.game_instance.stats_manager.add_dialogue_endstate(EndState.DECLINED_PROPOSE, dialogue.is_self_initiated)
        return result

    def on_decline(self, envelope: Envelope, dialogue: Dialogue) -> None:
        """
        Handle a Decline.

        :param envelope: the envelope containing the Decline
        :param dialogue: the dialogue

        :return: None
        """
        decline = envelope.message
        assert decline.protocol_id == "fipa" and decline.get("performative") == FIPAMessage.Performative.DECLINE
        logger.debug("[{}]: on_decline: msg_id={}, dialogue_id={}, origin={}, target={}"
                     .format(self.agent_name, decline.get("id"), decline.get("dialogue_id"), envelope.sender, decline.get("target")))
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

    def on_accept(self, envelope: Envelope, dialogue: Dialogue) -> List[Envelope]:
        """
        Handle an Accept.

        :param envelope: the envelope containing the Accept
        :param dialogue: the dialogue
        :return: a Decline, or an Accept and a Transaction, or a Transaction (in a Message object)
        """
        accept = envelope.message
        assert envelope.protocol_id == "fipa" \
            and accept.get("performative") == FIPAMessage.Performative.ACCEPT \
            and dialogue.dialogue_label in self.game_instance.transaction_manager.pending_proposals \
            and accept.get("target") in self.game_instance.transaction_manager.pending_proposals[dialogue.dialogue_label]
        logger.debug("[{}]: on_accept: msg_id={}, dialogue_id={}, origin={}, target={}"
                     .format(self.agent_name, accept.get("id"), accept.get("dialogue_id"), envelope.sender, accept.get("target")))
        new_msg_id = accept.get("id") + 1
        results = []
        transaction = self.game_instance.transaction_manager.pop_pending_proposal(dialogue.dialogue_label, accept.get("target"))
        is_profitable_transaction, message = self.game_instance.is_profitable_transaction(transaction, dialogue)
        logger.debug(message)
        if is_profitable_transaction:
            if self.game_instance.strategy.is_world_modeling:
                self.game_instance.world_state.update_on_initial_accept(transaction)
            logger.debug("[{}]: Locking the current state (as {}).".format(self.agent_name, dialogue.role))
            self.game_instance.transaction_manager.add_locked_tx(transaction, as_seller=dialogue.is_seller)
            results.append(Envelope(to=self.game_instance.controller_pbk, sender=self.crypto.public_key, protocol_id=ByteMessage.protocol_id,
                                    message=ByteMessage(message_id=STARTING_MESSAGE_ID, dialogue_id=accept.get("dialogue_id"), content=transaction.serialize())))
            results.append(Envelope(to=envelope.sender, sender=self.crypto.public_key, protocol_id=FIPAMessage.protocol_id,
                                    message=FIPAMessage(message_id=new_msg_id, dialogue_id=accept.get("dialogue_id"), target=accept.get("id"), performative=FIPAMessage.Performative.MATCH_ACCEPT)))
        else:
            logger.debug("[{}]: Decline the accept (as {}).".format(self.agent_name, dialogue.role))
            results.append(Envelope(to=envelope.sender, sender=self.crypto.public_key, protocol_id=FIPAMessage.protocol_id,
                                    message=FIPAMessage(message_id=new_msg_id, dialogue_id=accept.get("dialogue_id"), target=accept.get("id"), performative=FIPAMessage.Performative.DECLINE)))
            self.game_instance.stats_manager.add_dialogue_endstate(EndState.DECLINED_ACCEPT, dialogue.is_self_initiated)
        return results

    def on_match_accept(self, envelope: Envelope, dialogue: Dialogue) -> List[Envelope]:
        """
        Handle a matching Accept.

        :param envelope: the envelope containing the MatchAccept
        :param dialogue: the dialogue
        :return: a Transaction
        """
        match_accept = envelope.message
        assert envelope.protocol_id == "fipa" \
            and match_accept.get("performative") == FIPAMessage.Performative.MATCH_ACCEPT \
            and dialogue.dialogue_label in self.game_instance.transaction_manager.pending_initial_acceptances \
            and match_accept.get("target") in self.game_instance.transaction_manager.pending_initial_acceptances[dialogue.dialogue_label]
        logger.debug("[{}]: on_match_accept: msg_id={}, dialogue_id={}, origin={}, target={}"
                     .format(self.agent_name, match_accept.get("id"), match_accept.get("dialogue_id"), envelope.sender, match_accept.get("target")))
        results = []
        transaction = self.game_instance.transaction_manager.pop_pending_initial_acceptance(dialogue.dialogue_label, match_accept.get("target"))
        results.append(Envelope(to=self.game_instance.controller_pbk, sender=self.crypto.public_key, protocol_id=ByteMessage.protocol_id,
                       message=ByteMessage(message_id=STARTING_MESSAGE_ID, dialogue_id=match_accept.get("dialogue_id"), content=transaction.serialize())))
        return results

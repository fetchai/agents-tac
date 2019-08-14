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
from typing import Union, List

from tac.agents.v1.base.dialogues import Dialogue
from tac.agents.v1.base.game_instance import GameInstance
from tac.agents.v1.base.helpers import generate_transaction_id
from tac.agents.v1.base.stats_manager import EndState
from tac.agents.v1.mail.messages import OEFAgentPropose, OEFAgentAccept, OEFAgentDecline, OEFAgentByteMessage, \
    OEFAgentMessage, OEFAgentCfp
from tac.helpers.crypto import Crypto
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

    def on_cfp(self, cfp: OEFAgentCfp, dialogue: Dialogue) -> Union[OEFAgentPropose, OEFAgentDecline]:
        """
        Handle a CFP.

        :param cfp: the CFP
        :param dialogue: the dialogue

        :return: a Propose or a Decline
        """
        goods_description = self.game_instance.get_service_description(is_supply=dialogue.is_seller)
        new_msg_id = cfp.msg_id + 1
        decline = False
        cfp_services = json.loads(cfp.query.decode('utf-8'))
        if not self.game_instance.is_matching(cfp_services, goods_description):
            decline = True
            logger.debug("[{}]: Current holdings do not satisfy CFP query.".format(self.agent_name))
        else:
            proposal = self.game_instance.generate_proposal(cfp_services, dialogue.is_seller)
            if proposal is None:
                decline = True
                logger.debug("[{}]: Current strategy does not generate proposal that satisfies CFP query.".format(self.agent_name))

        if decline:
            logger.debug("[{}]: sending to {} a Decline{}".format(self.agent_name, cfp.destination,
                                                                  pprint.pformat({
                                                                      "msg_id": new_msg_id,
                                                                      "dialogue_id": cfp.dialogue_id,
                                                                      "origin": cfp.destination,
                                                                      "target": cfp.msg_id
                                                                  })))
            response = OEFAgentDecline(new_msg_id, cfp.dialogue_id, cfp.destination, cfp.msg_id)
            self.game_instance.stats_manager.add_dialogue_endstate(EndState.DECLINED_CFP, dialogue.is_self_initiated)
        else:
            transaction_id = generate_transaction_id(self.crypto.public_key, cfp.destination, dialogue.dialogue_label, dialogue.is_seller)
            transaction = Transaction.from_proposal(proposal=proposal,
                                                    transaction_id=transaction_id,
                                                    is_sender_buyer=not dialogue.is_seller,
                                                    counterparty=cfp.destination,
                                                    sender=self.crypto.public_key,
                                                    crypto=self.crypto)
            self.game_instance.transaction_manager.add_pending_proposal(dialogue.dialogue_label, new_msg_id, transaction)
            logger.debug("[{}]: sending to {} a Propose{}".format(self.agent_name, cfp.destination,
                                                                  pprint.pformat({
                                                                      "msg_id": new_msg_id,
                                                                      "dialogue_id": cfp.dialogue_id,
                                                                      "origin": cfp.destination,
                                                                      "target": cfp.msg_id,
                                                                      "propose": proposal.values
                                                                  })))
            response = OEFAgentPropose(new_msg_id, cfp.dialogue_id, cfp.destination, cfp.msg_id, [proposal])
        return response

    def on_propose(self, propose: OEFAgentPropose, dialogue: Dialogue) -> Union[OEFAgentAccept, OEFAgentDecline]:
        """
        Handle a Propose.

        :param propose: the Propose
        :param dialogue: the dialogue

        :return: an Accept or a Decline
        """
        logger.debug("[{}]: on propose as {}.".format(self.agent_name, dialogue.role))
        proposal = propose.proposal[0]
        transaction_id = generate_transaction_id(self.crypto.public_key, propose.destination, dialogue.dialogue_label, dialogue.is_seller)
        transaction = Transaction.from_proposal(proposal=proposal,
                                                transaction_id=transaction_id,
                                                is_sender_buyer=not dialogue.is_seller,
                                                counterparty=propose.destination,
                                                sender=self.crypto.public_key,
                                                crypto=self.crypto)
        new_msg_id = propose.msg_id + 1
        is_profitable_transaction, message = self.game_instance.is_profitable_transaction(transaction, dialogue)
        logger.debug(message)
        if is_profitable_transaction:
            logger.debug("[{}]: Accepting propose (as {}).".format(self.agent_name, dialogue.role))
            self.game_instance.transaction_manager.add_locked_tx(transaction, as_seller=dialogue.is_seller)
            self.game_instance.transaction_manager.add_pending_initial_acceptance(dialogue.dialogue_label, new_msg_id, transaction)
            result = OEFAgentAccept(new_msg_id, propose.dialogue_id, propose.destination, propose.msg_id)
        else:
            logger.debug("[{}]: Declining propose (as {})".format(self.agent_name, dialogue.role))
            result = OEFAgentDecline(new_msg_id, propose.dialogue_id, propose.destination, propose.msg_id)
            self.game_instance.stats_manager.add_dialogue_endstate(EndState.DECLINED_PROPOSE, dialogue.is_self_initiated)
        return result

    def on_decline(self, decline: OEFAgentDecline, dialogue: Dialogue) -> None:
        """
        Handle a Decline.

        :param decline: the decline
        :param dialogue: the dialogue

        :return: None
        """
        logger.debug("[{}]: on_decline: msg_id={}, dialogue_id={}, origin={}, target={}"
                     .format(self.agent_name, decline.msg_id, decline.dialogue_id, decline.destination, decline.target))

        if decline.target == 1:
            self.game_instance.stats_manager.add_dialogue_endstate(EndState.DECLINED_CFP, dialogue.is_self_initiated)
        elif decline.target == 2:
            self.game_instance.stats_manager.add_dialogue_endstate(EndState.DECLINED_PROPOSE, dialogue.is_self_initiated)
            transaction = self.game_instance.transaction_manager.pop_pending_proposal(dialogue.dialogue_label, decline.target)
            if self.game_instance.strategy.is_world_modeling:
                self.game_instance.world_state.update_on_declined_propose(transaction)
        elif decline.target == 3:
            self.game_instance.stats_manager.add_dialogue_endstate(EndState.DECLINED_ACCEPT, dialogue.is_self_initiated)
            transaction = self.game_instance.transaction_manager.pop_pending_initial_acceptance(dialogue.dialogue_label, decline.target)
            self.game_instance.transaction_manager.pop_locked_tx(transaction.transaction_id)

        return None

    def on_accept(self, accept: OEFAgentAccept, dialogue: Dialogue) -> Union[List[OEFAgentDecline], List[Union[OEFAgentAccept]], List[OEFAgentByteMessage]]:
        """
        Handle an Accept.

        :param accept: the accept
        :param dialogue: the dialogue

        :return: a Deline or an Accept and a Transaction (in OutContainer) or a Transaction (in OutContainer)
        """
        logger.debug("[{}]: on_accept: msg_id={}, dialogue_id={}, origin={}, target={}"
                     .format(self.agent_name, accept.msg_id, accept.dialogue_id, accept.destination, accept.target))

        if dialogue.dialogue_label in self.game_instance.transaction_manager.pending_initial_acceptances \
                and accept.target in self.game_instance.transaction_manager.pending_initial_acceptances[dialogue.dialogue_label]:
            results = self._on_match_accept(accept, dialogue)
        else:
            results = self._on_initial_accept(accept, dialogue)
        return results

    def _on_initial_accept(self, accept: OEFAgentAccept, dialogue: Dialogue) -> Union[List[OEFAgentDecline], List[Union[OEFAgentByteMessage, OEFAgentAccept]]]:
        """
        Handle an initial Accept.

        :param accept: the accept
        :param dialogue: the dialogue

        :return: a Deline or an Accept and a Transaction (in OutContainer
        """
        transaction = self.game_instance.transaction_manager.pop_pending_proposal(dialogue.dialogue_label, accept.target)
        new_msg_id = accept.msg_id + 1
        results = []
        is_profitable_transaction, message = self.game_instance.is_profitable_transaction(transaction, dialogue)
        logger.debug(message)
        if is_profitable_transaction:
            if self.game_instance.strategy.is_world_modeling:
                self.game_instance.world_state.update_on_initial_accept(transaction)
            logger.debug("[{}]: Locking the current state (as {}).".format(self.agent_name, dialogue.role))
            self.game_instance.transaction_manager.add_locked_tx(transaction, as_seller=dialogue.is_seller)
            results.append(OEFAgentByteMessage(STARTING_MESSAGE_ID, accept.dialogue_id, self.game_instance.controller_pbk, transaction.serialize()))
            results.append(OEFAgentAccept(new_msg_id, accept.dialogue_id, accept.destination, accept.msg_id))
        else:
            logger.debug("[{}]: Decline the accept (as {}).".format(self.agent_name, dialogue.role))
            results.append(OEFAgentDecline(new_msg_id, accept.dialogue_id, accept.destination, accept.msg_id))
            self.game_instance.stats_manager.add_dialogue_endstate(EndState.DECLINED_ACCEPT, dialogue.is_self_initiated)
        return results

    def _on_match_accept(self, accept: OEFAgentAccept, dialogue: Dialogue) -> List[OEFAgentMessage]:
        """
        Handle a matching Accept.

        :param accept: the accept
        :param dialogue: the dialogue

        :return: a Transaction
        """
        logger.debug("[{}]: on match accept".format(self.agent_name))
        results = []
        transaction = self.game_instance.transaction_manager.pop_pending_initial_acceptance(dialogue.dialogue_label, accept.target)
        results.append(OEFAgentByteMessage(STARTING_MESSAGE_ID, accept.dialogue_id, self.game_instance.controller_pbk, transaction.serialize()))
        return results

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

"""
This module contains the classes that implements the Controller agent behaviour.

The methods are split in three classes:
- AgentMessageDispatcher: class to wrap the decoding procedure and dispatching the handling of the message to the right function.
- GameHandler: handles an instance of the game.
- TACMessageHandler: abstract class for a TACMessage handler.
- RegisterHandler: class for a register handler.
- UnregisterHandler: class for an unregister handler
- TransactionHandler: class for a transaction handler.
- GetStateUpdateHandler: class for a state update handler.
"""

import datetime
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Any, Dict, Optional, List, Set, TYPE_CHECKING

from aea.agent import Liveness
from aea.crypto.base import Crypto
from aea.mail.base import Address, Envelope, MailBox
from aea.protocols.oef.message import OEFMessage
from aea.protocols.oef.serialization import OEFSerializer
from aea.protocols.tac.message import TACMessage
from aea.protocols.tac.serialization import TACSerializer
from tac.agents.controller.base.actions import OEFActions
from tac.agents.controller.base.helpers import generate_good_pbk_to_name
from tac.agents.controller.base.reactions import OEFReactions
from tac.agents.controller.base.states import Game
from tac.agents.controller.base.tac_parameters import TACParameters
from tac.gui.monitor import Monitor, NullMonitor
from tac.platform.game.base import GameData, GamePhase, Transaction
from tac.platform.game.stats import GameStats

if TYPE_CHECKING:
    from tac.agents.controller.agent import ControllerAgent

logger = logging.getLogger(__name__)


class TACMessageHandler(ABC):
    """Abstract class for a TACMessage handler."""

    def __init__(self, controller_agent: 'ControllerAgent') -> None:
        """
        Instantiate a TACMessage handler.

        :param controller_agent: the controller agent instance
        :return: None
        """
        self.controller_agent = controller_agent

    def __call__(self, message: TACMessage, sender: Address) -> None:
        """Call the handler."""
        return self.handle(message, sender)

    @abstractmethod
    def handle(self, message: TACMessage, sender: Address) -> None:
        """
        Handle a TACMessage from an OEF agent.

        :param message: the 'get agent state' TACMessage.
        :param sender: the public key of the sender
        :return: None
        """


class RegisterHandler(TACMessageHandler):
    """Class for a register handler."""

    def __init__(self, controller_agent: 'ControllerAgent') -> None:
        """Instantiate a RegisterHandler."""
        super().__init__(controller_agent)

    def handle(self, message: TACMessage, sender: Address) -> None:
        """
        Handle a register message.

        If the public key is already registered, answer with an error message.

        :param message: the 'get agent state' TACMessage.
        :param sender: the public key of the sender
        :return: None
        """
        whitelist = self.controller_agent.game_handler.tac_parameters.whitelist
        agent_name = message.get("agent_name")
        if whitelist is not None and agent_name not in whitelist:
            logger.error("[{}]: Agent name not in whitelist: '{}'".format(self.controller_agent.name, agent_name))
            tac_msg = TACMessage(tac_type=TACMessage.Type.TAC_ERROR, error_code=TACMessage.ErrorCode.AGENT_NAME_NOT_IN_WHITELIST)
            tac_bytes = TACSerializer().encode(tac_msg)
            self.controller_agent.mailbox.outbox.put_message(to=sender, sender=self.controller_agent.crypto.public_key, protocol_id=TACMessage.protocol_id, message=tac_bytes)

        if sender in self.controller_agent.game_handler.registered_agents:
            logger.error("[{}]: Agent already registered: '{}'".format(self.controller_agent.name, self.controller_agent.game_handler.agent_pbk_to_name[sender]))
            tac_msg = TACMessage(tac_type=TACMessage.Type.TAC_ERROR, error_code=TACMessage.ErrorCode.AGENT_PBK_ALREADY_REGISTERED)
            tac_bytes = TACSerializer().encode(tac_msg)
            self.controller_agent.mailbox.outbox.put_message(to=sender, sender=self.controller_agent.crypto.public_key, protocol_id=TACMessage.protocol_id, message=tac_bytes)

        if agent_name in self.controller_agent.game_handler.agent_pbk_to_name.values():
            logger.error("[{}]: Agent with this name already registered: '{}'".format(self.controller_agent.name, agent_name))
            tac_msg = TACMessage(tac_type=TACMessage.Type.TAC_ERROR, error_code=TACMessage.ErrorCode.AGENT_NAME_ALREADY_REGISTERED)
            tac_bytes = TACSerializer().encode(tac_msg)
            self.controller_agent.mailbox.outbox.put_message(to=sender, sender=self.controller_agent.crypto.public_key, protocol_id=TACMessage.protocol_id, message=tac_bytes)

        try:
            self.controller_agent.game_handler.monitor.dashboard.agent_pbk_to_name.update({sender: agent_name})
            self.controller_agent.game_handler.monitor.update()
        except Exception as e:
            logger.error(str(e))

        self.controller_agent.game_handler.agent_pbk_to_name[sender] = agent_name
        logger.debug("[{}]: Agent registered: '{}'".format(self.controller_agent.name, self.controller_agent.game_handler.agent_pbk_to_name[sender]))
        self.controller_agent.game_handler.registered_agents.add(sender)


class UnregisterHandler(TACMessageHandler):
    """Class for an unregister handler."""

    def __init__(self, controller_agent: 'ControllerAgent') -> None:
        """Instantiate an UnregisterHandler."""
        super().__init__(controller_agent)

    def handle(self, message: TACMessage, sender: Address) -> None:
        """
        Handle a unregister message.

        If the public key is not registered, answer with an error message.

        :param message: the 'get agent state' TACMessage.
        :param sender: the public key of the sender
        :return: None
        """
        if sender not in self.controller_agent.game_handler.registered_agents:
            logger.error("[{}]: Agent not registered: '{}'".format(self.controller_agent.name, sender))
            tac_msg = TACMessage(tac_type=TACMessage.Type.TAC_ERROR, error_code=TACMessage.ErrorCode.AGENT_NOT_REGISTERED)
            tac_bytes = TACSerializer().encode(tac_msg)
            self.controller_agent.mailbox.outbox.put_message(to=sender, sender=self.controller_agent.crypto.public_key, protocol_id=TACMessage.protocol_id, message=tac_bytes)
        else:
            logger.debug("[{}]: Agent unregistered: '{}'".format(self.controller_agent.name, self.controller_agent.game_handler.agent_pbk_to_name[sender]))
            self.controller_agent.game_handler.registered_agents.remove(sender)
            self.controller_agent.game_handler.agent_pbk_to_name.pop(sender)


class TransactionHandler(TACMessageHandler):
    """Class for a transaction handler."""

    def __init__(self, controller_agent: 'ControllerAgent') -> None:
        """Instantiate a TransactionHandler."""
        super().__init__(controller_agent)
        self._pending_transaction_requests = {}  # type: Dict[str, Transaction]

    def handle(self, message: TACMessage, sender: Address) -> None:
        """
        Handle a transaction TACMessage message.

        If the transaction is invalid (e.g. because the state of the game are not consistent), reply with an error.

        :param message: the 'get agent state' TACMessage.
        :param sender: the public key of the sender
        :return: None
        """
        transaction = Transaction.from_message(message, sender)
        logger.debug("[{}]: Handling transaction: {}".format(self.controller_agent.name, transaction))

        # if transaction arrives first time then put it into the pending pool
        if message.get("transaction_id") not in self._pending_transaction_requests:
            if self.controller_agent.game_handler.current_game.is_transaction_valid(transaction):
                logger.debug("[{}]: Put transaction TACMessage in the pool: {}".format(self.controller_agent.name, message.get("transaction_id")))
                self._pending_transaction_requests[message.get("transaction_id")] = transaction
            else:
                self._handle_invalid_transaction(message, sender)
        # if transaction arrives second time then process it
        else:
            pending_tx = self._pending_transaction_requests.pop(message.get("transaction_id"))
            if transaction.matches(pending_tx):
                if self.controller_agent.game_handler.current_game.is_transaction_valid(transaction):
                    self.controller_agent.game_handler.confirmed_transaction_per_participant[pending_tx.sender].append(pending_tx)
                    self.controller_agent.game_handler.confirmed_transaction_per_participant[transaction.sender].append(transaction)
                    self._handle_valid_transaction(message, sender, transaction)
                else:
                    self._handle_invalid_transaction(message, sender)
            else:
                self._handle_non_matching_transaction(message, sender)

    def _handle_valid_transaction(self, message: TACMessage, sender: Address, transaction: Transaction) -> None:
        """
        Handle a valid transaction.

        That is:
        - update the game state
        - send a transaction confirmation both to the buyer and the seller.

        :param tx: the transaction.
        :return: None
        """
        logger.debug("[{}]: Handling valid transaction: {}".format(self.controller_agent.name, message.get("transaction_id")))

        # update the game state.
        self.controller_agent.game_handler.current_game.settle_transaction(transaction)

        # update the dashboard monitor
        self.controller_agent.game_handler.monitor.update()

        # send the transaction confirmation.
        tac_msg = TACMessage(tac_type=TACMessage.Type.TRANSACTION_CONFIRMATION, transaction_id=message.get("transaction_id"))
        tac_bytes = TACSerializer().encode(tac_msg)
        self.controller_agent.outbox.put_message(to=sender, sender=self.controller_agent.crypto.public_key, protocol_id=TACMessage.protocol_id, message=tac_bytes)
        self.controller_agent.outbox.put_message(to=message.get("counterparty"), sender=self.controller_agent.crypto.public_key, protocol_id=TACMessage.protocol_id, message=tac_bytes)

        # log messages
        logger.debug("[{}]: Transaction '{}' settled successfully.".format(self.controller_agent.name, message.get("transaction_id")))
        holdings_summary = self.controller_agent.game_handler.current_game.get_holdings_summary()
        logger.debug("[{}]: Current state:\n{}".format(self.controller_agent.name, holdings_summary))

    def _handle_invalid_transaction(self, message: TACMessage, sender: Address) -> None:
        """Handle an invalid transaction."""
        tac_msg = TACMessage(tac_type=TACMessage.Type.TAC_ERROR, error_code=TACMessage.ErrorCode.TRANSACTION_NOT_VALID, details={"transaction_id": message.get("transaction_id")})
        tac_bytes = TACSerializer().encode(tac_msg)
        self.controller_agent.mailbox.outbox.put_message(to=sender, sender=self.controller_agent.crypto.public_key, protocol_id=TACMessage.protocol_id, message=tac_bytes)

    def _handle_non_matching_transaction(self, message: TACMessage, sender: Address) -> None:
        """Handle non-matching transaction."""
        tac_msg = TACMessage(tac_type=TACMessage.Type.TAC_ERROR, error_code=TACMessage.ErrorCode.TRANSACTION_NOT_MATCHING)
        tac_bytes = TACSerializer().encode(tac_msg)
        self.controller_agent.mailbox.outbox.put_message(to=sender, sender=self.controller_agent.crypto.public_key, protocol_id=TACMessage.protocol_id, message=tac_bytes)


class GetStateUpdateHandler(TACMessageHandler):
    """Class for a state update handler."""

    def handle(self, message: TACMessage, sender: Address) -> None:
        """
        Handle a 'get agent state' TACMessage.

        If the public key is not registered, answer with an error message.

        :param message: the 'get agent state' TACMessage.
        :param sender: the public key of the sender
        :return: None
        """
        logger.debug("[{}]: Handling the 'get agent state' TACMessage: {}".format(self.controller_agent.name, message))
        if not self.controller_agent.game_handler.is_game_running():
            logger.error("[{}]: GetStateUpdate TACMessage is not valid while the competition is not running.".format(self.controller_agent.name))
            tac_msg = TACMessage(tac_type=TACMessage.Type.TAC_ERROR, error_code=TACMessage.ErrorCode.COMPETITION_NOT_RUNNING)
        if sender not in self.controller_agent.game_handler.registered_agents:
            logger.error("[{}]: Agent not registered: '{}'".format(self.controller_agent.name, message.get("agent_name")))
            tac_msg = TACMessage(tac_type=TACMessage.Type.TAC_ERROR, error_code=TACMessage.ErrorCode.AGENT_NOT_REGISTERED)
        else:
            transactions = self.controller_agent.game_handler.confirmed_transaction_per_participant[sender]  # type: List[Transaction]
            initial_game_data = self.controller_agent.game_handler.game_data_per_participant[sender]  # type: Dict
            tac_msg = TACMessage(tac_type=TACMessage.Type.STATE_UPDATE, initial_state=initial_game_data, transactions=transactions)
        tac_bytes = TACSerializer().encode(tac_msg)
        self.controller_agent.mailbox.outbox.put_message(to=sender, sender=self.controller_agent.crypto.public_key, protocol_id=TACMessage.protocol_id, message=tac_bytes)


class AgentMessageDispatcher(object):
    """Class to wrap the decoding procedure and dispatching the handling of the message to the right function."""

    def __init__(self, controller_agent: 'ControllerAgent'):
        """
        Initialize a Controller handler, i.e. the class that manages the handling of incoming messages.

        :param controller_agent: The Controller Agent the handler is associated with.
        """
        self.controller_agent = controller_agent

        self.handlers = {
            TACMessage.Type.REGISTER: RegisterHandler(controller_agent),
            TACMessage.Type.UNREGISTER: UnregisterHandler(controller_agent),
            TACMessage.Type.TRANSACTION: TransactionHandler(controller_agent),
            TACMessage.Type.GET_STATE_UPDATE: GetStateUpdateHandler(controller_agent),
        }  # type: Dict[TACMessage.Type, TACMessageHandler]

    def handle_agent_message(self, envelope: Envelope) -> None:
        """
        Dispatch the TACMessage to the right handler.

        If no handler is found for the provided type of TACMessage, return an "invalid TACMessage" error.
        If something bad happen, return a "generic" error.

        :param envelope: the envelope to handle
        :return: None
        """
        assert envelope.protocol_id == "tac"
        tac_msg = TACSerializer().decode(envelope.message)
        logger.debug("[{}] on_message: origin={}" .format(self.controller_agent.name, envelope.sender))
        tac_msg_type = tac_msg.get("type")
        handle_tac_message = self.handlers.get(TACMessage.Type(tac_msg_type), None)  # type: TACMessageHandler
        if handle_tac_message is None:
            logger.debug("[{}]: Unknown message from {}".format(self.controller_agent.name, envelope.sender))
            tac_error = TACMessage(tac_type=TACMessage.Type.TAC_ERROR, error_code=TACMessage.ErrorCode.REQUEST_NOT_VALID.value)
            tac_bytes = TACSerializer().encode(tac_error)
            self.controller_agent.mailbox.outbox.put_message(to=envelope.sender, sender=self.controller_agent.crypto.public_key, protocol_id=tac_error.protocol_id, message=tac_bytes)
            return
        else:
            try:
                handle_tac_message(tac_msg, envelope.sender)
            except Exception as e:
                logger.debug("[{}]: Error caught: {}".format(self.controller_agent.name, str(e)))
                logger.exception(e)
                tac_error = TACMessage(tac_type=TACMessage.Type.TAC_ERROR, error_code=TACMessage.ErrorCode.GENERIC_ERROR.value)
                tac_bytes = TACSerializer().encode(tac_error)
                self.controller_agent.mailbox.outbox.put_message(to=envelope.sender, sender=self.controller_agent.crypto.public_key, protocol_id=tac_error.protocol_id, message=tac_bytes)


class GameHandler:
    """A class to manage a TAC instance."""

    def __init__(self, agent_name: str, crypto: Crypto, mailbox: MailBox, monitor: Monitor, tac_parameters: TACParameters) -> None:
        """
        Instantiate a GameHandler.

        :param agent_name: the name of the agent.
        :param crypto: the crypto module of the agent.
        :param mailbox: the mailbox.
        :param monitor: the monitor.
        :param tac_parameters: the tac parameters.
        :return: None
        """
        self.agent_name = agent_name
        self.crypto = crypto
        self.mailbox = mailbox
        self.monitor = monitor
        self.tac_parameters = tac_parameters
        self.competition_start = None
        self._game_phase = GamePhase.PRE_GAME

        self.registered_agents = set()  # type: Set[str]
        self.agent_pbk_to_name = defaultdict()  # type: Dict[str, str]
        self.good_pbk_to_name = generate_good_pbk_to_name(self.tac_parameters.nb_goods)  # type: Dict[str, str]
        self.current_game = None  # type: Optional[Game]
        self.inactivity_timeout_timedelta = datetime.timedelta(seconds=tac_parameters.inactivity_timeout) \
            if tac_parameters.inactivity_timeout is not None else datetime.timedelta(seconds=15)

        self.game_data_per_participant = {}  # type: Dict[str, GameData]
        self.confirmed_transaction_per_participant = defaultdict(lambda: [])  # type: Dict[str, List[Transaction]]

        self.monitor = NullMonitor() if monitor is None else monitor  # type: Monitor
        self.monitor.start(None)
        self.monitor.update()

    def reset(self) -> None:
        """Reset the game."""
        self.current_game = None
        self.registered_agents = set()
        self.agent_pbk_to_name = defaultdict()
        self.good_pbk_to_name = defaultdict()

    @property
    def game_phase(self) -> GamePhase:
        """Get the game phase."""
        return self._game_phase

    @property
    def is_game_running(self) -> bool:
        """
        Check if an instance of a game is already set up.

        :return: Return True if there is a game running, False otherwise.
        """
        return self.current_game is not None

    def start_competition(self):
        """Create a game and send the game setting to every registered agent."""
        # assert that there is no competition running.
        assert not self.is_game_running
        self.current_game = self._create_game()

        try:
            self.monitor.set_gamestats(GameStats(self.current_game))
            self.monitor.update()
        except Exception as e:
            logger.exception(e)

        self._send_game_data_to_agents()

        self._game_phase = GamePhase.GAME
        # log messages
        logger.debug("[{}]: Started competition:\n{}".format(self.agent_name, self.current_game.get_holdings_summary()))
        logger.debug("[{}]: Computed equilibrium:\n{}".format(self.agent_name, self.current_game.get_equilibrium_summary()))

    def _create_game(self) -> Game:
        """
        Create a TAC game.

        :return: a Game instance.
        """
        nb_agents = len(self.registered_agents)

        game = Game.generate_game(nb_agents,
                                  self.tac_parameters.nb_goods,
                                  self.tac_parameters.tx_fee,
                                  self.tac_parameters.money_endowment,
                                  self.tac_parameters.base_good_endowment,
                                  self.tac_parameters.lower_bound_factor,
                                  self.tac_parameters.upper_bound_factor,
                                  self.agent_pbk_to_name,
                                  self.good_pbk_to_name)

        return game

    def _send_game_data_to_agents(self) -> None:
        """
        Send the data of every agent about the game (e.g. endowments, preferences, scores).

        Assuming that the agent labels are public keys of the OEF Agents.

        :return: None.
        """
        for public_key in self.current_game.configuration.agent_pbks:
            agent_state = self.current_game.get_agent_state_from_agent_pbk(public_key)
            game_data_response = GameData(
                public_key,
                agent_state.balance,
                agent_state.current_holdings,
                agent_state.utility_params,
                self.current_game.configuration.nb_agents,
                self.current_game.configuration.nb_goods,
                self.current_game.configuration.tx_fee,
                self.current_game.configuration.agent_pbk_to_name,
                self.current_game.configuration.good_pbk_to_name
            )
            logger.debug("[{}]: sending GameData to '{}': {}"
                         .format(self.agent_name, public_key, str(game_data_response)))
            self.game_data_per_participant[public_key] = game_data_response

            msg = TACMessage(tac_type=TACMessage.Type.GAME_DATA,
                             money=agent_state.balance,
                             endowment=agent_state.current_holdings,
                             utility_params=agent_state.utility_params,
                             nb_agents=self.current_game.configuration.nb_agents,
                             nb_goods=self.current_game.configuration.nb_goods,
                             tx_fee=self.current_game.configuration.tx_fee,
                             agent_pbk_to_name=self.current_game.configuration.agent_pbk_to_name,
                             good_pbk_to_name=self.current_game.configuration.good_pbk_to_name
                             )
            tac_bytes = TACSerializer().encode(msg)
            self.mailbox.outbox.put_message(to=public_key, sender=self.crypto.public_key, protocol_id=TACMessage.protocol_id, message=tac_bytes)

    def notify_competition_cancelled(self):
        """Notify agents that the TAC is cancelled."""
        logger.debug("[{}]: Notifying agents that TAC is cancelled.".format(self.agent_name))
        for agent_pbk in self.registered_agents:
            tac_msg = TACMessage(tac_type=TACMessage.Type.CANCELLED)
            tac_bytes = TACSerializer().encode(tac_msg)
            self.mailbox.outbox.put_message(to=agent_pbk, sender=self.crypto.public_key, protocol_id=TACMessage.protocol_id, message=tac_bytes)
        # wait some time to make sure the connection delivers the messages
        time.sleep(2.0)
        self._game_phase = GamePhase.POST_GAME

    def simulation_dump(self) -> None:
        """
        Dump the details of the simulation.

        :return: None.
        """
        experiment_id = str(self.tac_parameters.experiment_id) if self.tac_parameters.experiment_id is not None else str(datetime.datetime.now())
        experiment_dir = self.tac_parameters.data_output_dir + "/" + experiment_id

        if not self.is_game_running:
            logger.warning("[{}]: Game not present. Using empty dictionary.".format(self.agent_name))
            game_dict = {}  # type: Dict[str, Any]
        else:
            game_dict = self.current_game.to_dict()

        os.makedirs(experiment_dir, exist_ok=True)
        with open(os.path.join(experiment_dir, "game.json"), "w") as f:
            json.dump(game_dict, f)


class OEFHandler(OEFActions, OEFReactions):
    """Handle the message exchange with the OEF."""

    def __init__(self, crypto: Crypto, liveness: Liveness, mailbox: MailBox, agent_name: str):
        """
        Instantiate the OEFHandler.

        :param crypto: the crypto module
        :param liveness: the liveness module
        :param mailbox: the mailbox
        :param agent_name: the agent name
        """
        OEFActions.__init__(self, crypto, liveness, mailbox, agent_name)
        OEFReactions.__init__(self, crypto, liveness, mailbox, agent_name)

    def handle_oef_message(self, envelope: Envelope) -> None:
        """
        Handle messages from the oef.

        The oef does not expect a response for any of these messages.

        :param envelope: the OEF message

        :return: None
        """
        logger.debug("[{}]: Handling OEF message. type={}".format(self.agent_name, type(envelope)))
        assert envelope.protocol_id == "oef"
        msg = OEFSerializer().decode(envelope.message)
        if msg.get("type") == OEFMessage.Type.OEF_ERROR:
            self.on_oef_error(envelope)
        elif msg.get("type") == OEFMessage.Type.DIALOGUE_ERROR:
            self.on_dialogue_error(envelope)
        else:
            logger.warning("[{}]: OEF Message type not recognized.".format(self.agent_name))

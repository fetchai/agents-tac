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
- RequestHandler: abstract class for a request handler.
- RegisterHandler: class for a register handler.
- UnregisterHandler: class for an unregister handler
- TransactionHandler: class for a transaction handler.
- GetStateUpdateHandler: class for a state update handler.
"""

import datetime
import json
import logging
import os
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Any, Dict, Optional, List, Set, Type, TYPE_CHECKING

from tac.aea.agent import Liveness
from tac.aea.crypto.base import Crypto
from tac.aea.mail.base import MailBox
from tac.aea.mail.messages import ByteMessage, OEFMessage
from tac.aea.mail.protocol import Envelope
from tac.agents.controller.base.actions import OEFActions
from tac.agents.controller.base.helpers import generate_good_pbk_to_name
from tac.agents.controller.base.reactions import OEFReactions
from tac.agents.controller.base.states import Game
from tac.agents.controller.base.tac_parameters import TACParameters
from tac.gui.monitor import Monitor, NullMonitor
from tac.platform.game.base import GamePhase
from tac.platform.game.stats import GameStats
from tac.platform.protocol import Response, Request, Register, Unregister, Error, GameData, \
    Transaction, TransactionConfirmation, ErrorCode, Cancelled, GetStateUpdate, StateUpdate, TacMessage

if TYPE_CHECKING:
    from tac.platform.controller.controller_agent import ControllerAgent

logger = logging.getLogger(__name__)


class RequestHandler(ABC):
    """Abstract class for a request handler."""

    def __init__(self, controller_agent: 'ControllerAgent') -> None:
        """
        Instantiate a request handler.

        :param controller_agent: the controller agent instance
        :return: None
        """
        self.controller_agent = controller_agent

    def __call__(self, request: Request) -> Optional[Response]:
        """Call the handler."""
        return self.handle(request)

    @abstractmethod
    def handle(self, request: Request) -> Optional[Response]:
        """
        Handle a request from an OEF agent.

        :param request: the request message.
        :return: a response, or None.
        """


class RegisterHandler(RequestHandler):
    """Class for a register handler."""

    def handle(self, request: Register) -> Optional[Response]:
        """
        Handle a register message.

        If the public key is already registered, answer with an error message.
        If this is the n_th registration request, where n is equal to nb_agents, then start the competition.

        :param request: the register request.
        :return: an Error response if an error occurred, else None.
        """
        whitelist = self.controller_agent.game_handler.tac_parameters.whitelist
        if whitelist is not None and request.agent_name not in whitelist:
            error_msg = "[{}]: Agent name not in whitelist: '{}'".format(self.controller_agent.name, request.agent_name)
            logger.error(error_msg)
            return Error(request.public_key, self.controller_agent.crypto, ErrorCode.AGENT_NAME_NOT_IN_WHITELIST)

        if request.public_key in self.controller_agent.game_handler.registered_agents:
            error_msg = "[{}]: Agent already registered: '{}'".format(self.controller_agent.name, self.controller_agent.game_handler.agent_pbk_to_name[request.public_key])
            logger.error(error_msg)
            return Error(request.public_key, self.controller_agent.crypto, ErrorCode.AGENT_PBK_ALREADY_REGISTERED)

        if request.agent_name in self.controller_agent.game_handler.agent_pbk_to_name.values():
            error_msg = "[{}]: Agent with this name already registered: '{}'".format(self.controller_agent.name, request.agent_name)
            logger.error(error_msg)
            return Error(request.public_key, self.controller_agent.crypto, ErrorCode.AGENT_NAME_ALREADY_REGISTERED)

        try:
            self.controller_agent.game_handler.monitor.dashboard.agent_pbk_to_name.update({request.public_key: request.agent_name})
            self.controller_agent.game_handler.monitor.update()
        except Exception as e:
            logger.error(str(e))

        self.controller_agent.game_handler.agent_pbk_to_name[request.public_key] = request.agent_name
        logger.debug("[{}]: Agent registered: '{}'".format(self.controller_agent.name, self.controller_agent.game_handler.agent_pbk_to_name[request.public_key]))
        self.controller_agent.game_handler.registered_agents.add(request.public_key)
        return None


class UnregisterHandler(RequestHandler):
    """Class for an unregister handler."""

    def handle(self, request: Unregister) -> Optional[Response]:
        """
        Handle a unregister message.

        If the public key is not registered, answer with an error message.

        :param request: the register request.
        :return: an Error response if an error occurred, else None.
        """
        if request.public_key not in self.controller_agent.game_handler.registered_agents:
            error_msg = "[{}]: Agent not registered: '{}'".format(self.controller_agent.name, request.public_key)
            logger.error(error_msg)
            return Error(request.public_key, self.controller_agent.crypto, ErrorCode.AGENT_NOT_REGISTERED)
        else:
            logger.debug("[{}]: Agent unregistered: '{}'".format(self.controller_agent.name, self.controller_agent.game_handler.agent_pbk_to_name[request.public_key]))
            self.controller_agent.game_handler.registered_agents.remove(request.public_key)
            self.controller_agent.game_handler.agent_pbk_to_name.pop(request.public_key)
            return None


class TransactionHandler(RequestHandler):
    """Class for a transaction handler."""

    def __init__(self, controller_agent: 'ControllerAgent') -> None:
        """Instantiate a TransactionHandler."""
        super().__init__(controller_agent)
        self._pending_transaction_requests = {}  # type: Dict[str, Transaction]

    def handle(self, tx: Transaction) -> Optional[Response]:
        """
        Handle a transaction request message.

        If the transaction is invalid (e.g. because the state of the game are not consistent), reply with an error.

        :param request: the transaction request.
        :return: an Error response if an error occurred, else None (no response to send back).
        """
        logger.debug("[{}]: Handling transaction: {}".format(self.controller_agent.name, tx))

        # if transaction arrives first time then put it into the pending pool
        if tx.transaction_id not in self._pending_transaction_requests:
            if self.controller_agent.game_handler.current_game.is_transaction_valid(tx):
                logger.debug("[{}]: Put transaction request in the pool: {}".format(self.controller_agent.name, tx.transaction_id))
                self._pending_transaction_requests[tx.transaction_id] = tx
            else:
                return self._handle_invalid_transaction(tx)
        # if transaction arrives second time then process it
        else:
            pending_tx = self._pending_transaction_requests.pop(tx.transaction_id)
            if tx.matches(pending_tx):
                if self.controller_agent.game_handler.current_game.is_transaction_valid(tx):
                    self.controller_agent.game_handler.confirmed_transaction_per_participant[pending_tx.sender].append(pending_tx)
                    self.controller_agent.game_handler.confirmed_transaction_per_participant[tx.sender].append(tx)
                    self._handle_valid_transaction(tx)
                else:
                    return self._handle_invalid_transaction(tx)
            else:
                return self._handle_non_matching_transaction(tx)

    def _handle_valid_transaction(self, tx: Transaction) -> None:
        """
        Handle a valid transaction.

        That is:
        - update the game state
        - send a transaction confirmation both to the buyer and the seller.

        :param tx: the transaction.
        :return: None
        """
        logger.debug("[{}]: Handling valid transaction: {}".format(self.controller_agent.name, tx.transaction_id))

        # update the game state.
        self.controller_agent.game_handler.current_game.settle_transaction(tx)

        # update the dashboard monitor
        self.controller_agent.game_handler.monitor.update()

        # send the transaction confirmation.
        tx_confirmation = TransactionConfirmation(tx.public_key, self.controller_agent.crypto, tx.transaction_id)
        self.controller_agent.outbox.put_message(to=tx.public_key, sender=self.controller_agent.crypto.public_key, protocol_id=TacMessage.protocol_id,
                                                 message=TacMessage(tac_message=tx_confirmation))
        self.controller_agent.outbox.put_message(to=tx.counterparty, sender=self.controller_agent.crypto.public_key, protocol_id=TacMessage.protocol_id,
                                                 message=TacMessage(tac_message=tx_confirmation))
        # log messages
        logger.debug("[{}]: Transaction '{}' settled successfully.".format(self.controller_agent.name, tx.transaction_id))
        holdings_summary = self.controller_agent.game_handler.current_game.get_holdings_summary()
        logger.debug("[{}]: Current state:\n{}".format(self.controller_agent.name, holdings_summary))

        return None

    def _handle_invalid_transaction(self, tx: Transaction) -> Response:
        """Handle an invalid transaction."""
        return Error(tx.public_key, self.controller_agent.crypto, ErrorCode.TRANSACTION_NOT_VALID,
                     details={"transaction_id": tx.transaction_id})

    def _handle_non_matching_transaction(self, tx: Transaction) -> Response:
        """Handle non-matching transaction."""
        return Error(tx.public_key, self.controller_agent.crypto, ErrorCode.TRANSACTION_NOT_MATCHING)


class GetStateUpdateHandler(RequestHandler):
    """Class for a state update handler."""

    def handle(self, request: GetStateUpdate) -> Optional[Response]:
        """
        Handle a 'get agent state' request.

        If the public key is not registered, answer with an error message.

        :param request: the 'get agent state' request.
        :return: an Error response if an error occurred, else None.
        """
        logger.debug("[{}]: Handling the 'get agent state' request: {}".format(self.controller_agent.name, request))
        if not self.controller_agent.game_handler.is_game_running():
            error_msg = "[{}]: GetStateUpdate request is not valid while the competition is not running.".format(self.controller_agent.name)
            logger.error(error_msg)
            return Error(request.public_key, self.controller_agent.crypto, ErrorCode.COMPETITION_NOT_RUNNING)
        if request.public_key not in self.controller_agent.game_handler.registered_agents:
            error_msg = "[{}]: Agent not registered: '{}'".format(self.controller_agent.name, request.public_key)
            logger.error(error_msg)
            return Error(request.public_key, self.controller_agent.crypto, ErrorCode.AGENT_NOT_REGISTERED)
        else:
            transactions = self.controller_agent.game_handler.confirmed_transaction_per_participant[request.public_key]  # type: List[Transaction]
            initial_game_data = self.controller_agent.game_handler.game_data_per_participant[request.public_key]  # type: GameData
            return StateUpdate(request.public_key, self.controller_agent.crypto, initial_game_data, transactions)


class AgentMessageDispatcher(object):
    """Class to wrap the decoding procedure and dispatching the handling of the message to the right function."""

    def __init__(self, controller_agent: 'ControllerAgent'):
        """
        Initialize a Controller handler, i.e. the class that manages the handling of incoming messages.

        :param controller_agent: The Controller Agent the handler is associated with.
        """
        self.controller_agent = controller_agent

        self.handlers = {
            Register: RegisterHandler(controller_agent),
            Unregister: UnregisterHandler(controller_agent),
            Transaction: TransactionHandler(controller_agent),
            GetStateUpdate: GetStateUpdateHandler(controller_agent),
        }  # type: Dict[Type[Request], RequestHandler]

    def handle_agent_message(self, envelope: Envelope) -> Response:
        """
        Dispatch the request to the right handler.

        If no handler is found for the provided type of request, return an "invalid request" error.
        If something bad happen, return a "generic" error.

        :param envelope: the request to handle
        :return: the response.
        """
        assert envelope.protocol_id == "bytes"
        msg_id = envelope.message.get("id")
        dialogue_id = envelope.message.get("dialogue_id")
        sender = envelope.sender
        logger.debug("[{}] on_message: msg_id={}, dialogue_id={}, origin={}" .format(self.controller_agent.name, envelope.message.get("id"), dialogue_id, sender))
        request = self.decode(envelope.message.get("content"), sender)
        handle_request = self.handlers.get(type(request), None)  # type: RequestHandler
        if handle_request is None:
            logger.debug("[{}]: Unknown message: msg_id={}, dialogue_id={}, origin={}".format(self.controller_agent.name, msg_id, dialogue_id, sender))
            return Error(envelope.sender, self.controller_agent.crypto, ErrorCode.REQUEST_NOT_VALID)
        try:
            return handle_request(request)
        except Exception as e:
            logger.debug("[{}]: Error caught: {}".format(self.controller_agent.name, str(e)))
            logger.exception(e)
            return Error(sender, self.controller_agent.crypto, ErrorCode.GENERIC_ERROR)

    def decode(self, msg: bytes, public_key: str) -> Request:
        """
        From bytes to a Request message.

        :param msg: the serialized message.
        :param public_key: the public key of the sender agent.
        :return: the deserialized Request
        """
        request = Request.from_pb(msg, public_key, self.controller_agent.crypto)
        return request


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
                self.crypto,
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
            self.mailbox.outbox.put_message(to=public_key, sender=self.crypto.public_key, protocol_id=TacMessage.protocol_id,
                                            message=TacMessage(tac_message=game_data_response))

    def notify_competition_cancelled(self):
        """Notify agents that the TAC is cancelled."""
        logger.debug("[{}]: Notifying agents that TAC is cancelled.".format(self.agent_name))
        for agent_pbk in self.registered_agents:
            self.mailbox.outbox.put_message(to=agent_pbk, sender=self.crypto.public_key, protocol_id=TacMessage.protocol_id,
                                            message=TacMessage(tac_message=Cancelled(agent_pbk, self.crypto)))
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
        if envelope.message.get("type") == OEFMessage.Type.OEF_ERROR:
            self.on_oef_error(envelope)
        elif envelope.message.get("type") == OEFMessage.Type.DIALOGUE_ERROR:
            self.on_dialogue_error(envelope)
        else:
            logger.warning("[{}]: OEF Message type not recognized.".format(self.agent_name))

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
- ControllerAgent: extends OEFAgent, receives messages and sends them to the ControllerHandler.
- ControllerHandler: dispatches the handling of the message to the right handler.
- GameHandler: handles an instance of the game.
"""

import argparse
import asyncio
import datetime
import json
import logging
import os
import pprint
import random
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from threading import Thread
from typing import Any, Dict, Type, List
from typing import Optional, Set

import dateutil
from oef.agents import OEFAgent
from oef.schema import Description, DataModel, AttributeSchema

from tac.gui.monitor import Monitor, NullMonitor, VisdomMonitor
from tac.helpers.crypto import Crypto
from tac.helpers.misc import generate_good_pbk_to_name
from tac.platform.game import Game, GameTransaction
from tac.platform.protocol import Response, Request, Register, Unregister, Error, GameData, \
    Transaction, TransactionConfirmation, ErrorCode, Cancelled, GetStateUpdate, StateUpdate
from tac.platform.stats import GameStats

if __name__ != "__main__":
    logger = logging.getLogger(__name__)
else:
    logger = logging.getLogger("tac.platform.controller")


class TACParameters(object):
    """This class contains the parameters for the TAC."""

    def __init__(self, min_nb_agents: int = 5,
                 money_endowment: int = 200,
                 nb_goods: int = 5,
                 tx_fee: float = 1.0,
                 base_good_endowment: int = 2,
                 lower_bound_factor: int = 1,
                 upper_bound_factor: int = 1,
                 start_time: datetime.datetime = datetime.datetime.now(),
                 registration_timeout: int = 10,
                 competition_timeout: int = 20,
                 inactivity_timeout: int = 10,
                 whitelist: Optional[Set[str]] = None):
        """
        Initialize parameters for TAC.

        :param min_nb_agents: the number of agents to wait for the registration.
        :param money_endowment: The money amount every agent receives.
        :param nb_goods: the number of goods in the competition.
        :param tx_fee: the fee for a transaction.
        :param base_good_endowment:The base amount of per good instances every agent receives.
        :param lower_bound_factor: the lower bound factor of a uniform distribution.
        :param upper_bound_factor: the upper bound factor of a uniform distribution.
        :param start_time: the datetime when the competition will start.
        :param registration_timeout: the duration (in seconds) of the registration phase.
        :param competition_timeout: the duration (in seconds) of the competition phase.
        :param inactivity_timeout: the time when the competition will start.
        :param whitelist: the set of agent names allowed. If None, no checks on the agent names.
        """
        self._min_nb_agents = min_nb_agents
        self._money_endowment = money_endowment
        self._nb_goods = nb_goods
        self._tx_fee = tx_fee
        self._base_good_endowment = base_good_endowment
        self._lower_bound_factor = lower_bound_factor
        self._upper_bound_factor = upper_bound_factor
        self._start_time = start_time
        self._registration_timeout = registration_timeout
        self._competition_timeout = competition_timeout
        self._inactivity_timeout = inactivity_timeout
        self._whitelist = whitelist
        self._check_values()

    def _check_values(self) -> None:
        """
        Check constructor parameters.

        :raises ValueError: if some parameter has not the right value.
        """
        if self._start_time is None:
            raise ValueError
        if self._inactivity_timeout is None:
            raise ValueError

    @property
    def min_nb_agents(self) -> int:
        """Minimum number of agents required for a TAC instance."""
        return self._min_nb_agents

    @property
    def money_endowment(self):
        """Money endowment per agent for a TAC instance."""
        return self._money_endowment

    @property
    def nb_goods(self):
        """Good number for a TAC instance."""
        return self._nb_goods

    @property
    def tx_fee(self):
        """Transaction fee for a TAC instance."""
        return self._tx_fee

    @property
    def base_good_endowment(self):
        """Minimum endowment of each agent for each good."""
        return self._base_good_endowment

    @property
    def lower_bound_factor(self):
        """Lower bound of a uniform distribution."""
        return self._lower_bound_factor

    @property
    def upper_bound_factor(self):
        """Upper bound of a uniform distribution."""
        return self._upper_bound_factor

    @property
    def start_time(self) -> datetime.datetime:
        """TAC start time."""
        return self._start_time

    @property
    def end_time(self) -> datetime.datetime:
        """TAC end time."""
        return self._start_time + self.registration_timedelta + self.competition_timedelta

    @property
    def registration_timeout(self):
        """Timeout of registration."""
        return self._registration_timeout

    @property
    def competition_timeout(self):
        """Timeout of competition."""
        return self._competition_timeout

    @property
    def inactivity_timeout(self):
        """Timeout of agent inactivity from controller perspective (no received transactions)."""
        return self._inactivity_timeout

    @property
    def registration_timedelta(self) -> datetime.timedelta:
        """Time delta of the registration timeout."""
        return datetime.timedelta(0, self._registration_timeout)

    @property
    def competition_timedelta(self) -> datetime.timedelta:
        """Time delta of the competition timeout."""
        return datetime.timedelta(0, self._competition_timeout)

    @property
    def inactivity_timedelta(self) -> datetime.timedelta:
        """Time delta of the inactivity timeout."""
        return datetime.timedelta(0, self._inactivity_timeout)

    @property
    def whitelist(self) -> Optional[Set[str]]:
        """Whitelist of agent public keys allowed into the TAC instance."""
        return self._whitelist


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
            self.controller_agent.monitor.dashboard.agent_pbk_to_name.update({request.public_key: request.agent_name})
            self.controller_agent.monitor.update()
        except Exception as e:
            logger.error(str(e))

        self.controller_agent.game_handler.agent_pbk_to_name[request.public_key] = request.agent_name
        logger.debug("[{}]: Agent registered: '{}'".format(self.controller_agent.name, self.controller_agent.game_handler.agent_pbk_to_name[request.public_key]))
        self.controller_agent.game_handler.registered_agents.add(request.public_key)
        return None


class UnregisterHandler(RequestHandler):
    """Class for a unregister handler."""

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

    def handle(self, request: Transaction) -> Optional[Response]:
        """
        Handle a transaction request message.

        If the transaction is invalid (e.g. because the state of the game are not consistent), reply with an error.

        :param request: the transaction request.
        :return: an Error response if an error occurred, else None (no response to send back).
        """
        logger.debug("[{}]: Handling transaction: {}".format(self.controller_agent.name, request))

        # if transaction arrives first time then put it into the pending pool
        if request.transaction_id not in self._pending_transaction_requests:
            logger.debug("[{}]: Put transaction request in the pool: {}".format(self.controller_agent.name, request.transaction_id))
            self._pending_transaction_requests[request.transaction_id] = request
        # if transaction arrives second time then process it
        else:
            # TODO how to handle failures in matching transaction?
            #   that is, should the pending txs be removed from the pool?
            #       if yes, should the senders be notified and how?
            #  don't care for now, because assuming only (properly implemented) baseline agents.
            pending_tx = self._pending_transaction_requests.pop(request.transaction_id)
            if request.matches(pending_tx):
                tx = GameTransaction.from_request_to_game_tx(request)
                if self.controller_agent.game_handler.current_game.is_transaction_valid(tx):
                    self.controller_agent.game_handler.confirmed_transaction_per_participant[pending_tx.sender].append(pending_tx)
                    self.controller_agent.game_handler.confirmed_transaction_per_participant[request.sender].append(request)
                    self._handle_valid_transaction(request)
                else:
                    return self._handle_invalid_transaction(request)
            else:
                return self._handle_non_matching_transaction(request)

    def _handle_valid_transaction(self, request: Transaction) -> None:
        """
        Handle a valid transaction.

        That is:
        - update the game state
        - send a transaction confirmation both to the buyer and the seller.

        :param request: the transaction request.
        :return: None
        """
        logger.debug("[{}]: Handling valid transaction: {}".format(self.controller_agent.name, request.transaction_id))

        # update the game state.
        tx = GameTransaction.from_request_to_game_tx(request)
        self.controller_agent.game_handler.current_game.settle_transaction(tx)

        # update the GUI monitor
        self.controller_agent.monitor.update()

        # send the transaction confirmation.
        tx_confirmation = TransactionConfirmation(request.public_key, self.controller_agent.crypto, request.transaction_id)
        self.controller_agent.send_message(0, 0, request.public_key, tx_confirmation.serialize())
        self.controller_agent.send_message(0, 0, request.counterparty, tx_confirmation.serialize())

        # log messages
        logger.debug("[{}]: Transaction '{}' settled successfully.".format(self.controller_agent.name, request.transaction_id))
        holdings_summary = self.controller_agent.game_handler.current_game.get_holdings_summary()
        logger.debug("[{}]: Current state:\n{}".format(self.controller_agent.name, holdings_summary))

        return None

    def _handle_invalid_transaction(self, request: Transaction) -> Response:
        """Handle an invalid transaction."""
        return Error(request.public_key, self.controller_agent.crypto, ErrorCode.TRANSACTION_NOT_VALID,
                     details={"transaction_id": request.transaction_id})

    def _handle_non_matching_transaction(self, request: Transaction) -> Response:
        """Handle non-matching transaction."""
        return Error(request.public_key, self.controller_agent.crypto, ErrorCode.TRANSACTION_NOT_MATCHING)


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


class ControllerDispatcher(object):
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

    def register_handler(self, request_type: Type[Request], request_handler: RequestHandler) -> None:
        """
        Register a handler for a type of request.

        :param request_type: the type of request to handle.
        :param request_handler: the handler associated with the type specified.
        :return: None
        """
        self.handlers[request_type] = request_handler

    def process_request(self, msg: bytes, public_key: str) -> Response:
        """
        Handle a simple message coming from an agent.

        :param msg: the Protobuf message.
        :param public_key: the agent's public key that sent the request.
        :return: the Response object
        """
        message = self.decode(msg, public_key)  # type: Request
        response = self.dispatch(message)
        logger.debug("[{}]: Returning response: {}".format(self.controller_agent.name, str(response)))
        return response

    def dispatch(self, request: Request) -> Response:
        """
        Dispatch the request to the right handler.

        If no handler is found for the provided type of request, return an "invalid request" error.
        If something bad happen, return a "generic" error.

        :param request: the request to handle
        :return: the response.
        """
        handle_request = self.handlers.get(type(request), None)  # type: RequestHandler
        if handle_request is None:
            return Error(request.public_key, self.controller_agent.crypto, ErrorCode.REQUEST_NOT_VALID)
        try:
            return handle_request(request)
        except Exception as e:
            logger.debug("[{}]: Error caught: {}".format(self.controller_agent.name, str(e)))
            logger.exception(e)
            return Error(request.public_key, self.controller_agent.crypto, ErrorCode.GENERIC_ERROR)

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

    def __init__(self, controller_agent: 'ControllerAgent', tac_parameters: TACParameters) -> None:
        """
        Instantiate a GameHandler.

        :param controller_agent: the controller agent the handler is associated with.
        :param tac_parameters: the tac parameters
        :return: None
        """
        self.controller_agent = controller_agent
        self.tac_parameters = tac_parameters

        self.registered_agents = set()  # type: Set[str]
        self.agent_pbk_to_name = defaultdict()  # type: Dict[str, str]
        self.good_pbk_to_name = generate_good_pbk_to_name(self.tac_parameters.nb_goods)  # type: Dict[str, str]
        self.current_game = None  # type: Optional[Game]
        self.inactivity_timeout_timedelta = datetime.timedelta(seconds=tac_parameters.inactivity_timeout) \
            if tac_parameters.inactivity_timeout is not None else datetime.timedelta(seconds=15)

        self.game_data_per_participant = {}  # type: Dict[str, GameData]
        self.confirmed_transaction_per_participant = defaultdict(lambda: [])  # type: Dict[str, List[Transaction]]

    def reset(self) -> None:
        """Reset the game."""
        self.current_game = None
        self.registered_agents = set()
        self.agent_pbk_to_name = defaultdict()
        self.good_pbk_to_name = defaultdict()

    def is_game_running(self) -> bool:
        """
        Check if an instance of a game is already set up.

        :return: Return True if there is a game running, False otherwise.
        """
        return self.current_game is not None

    def _start_competition(self):
        """Create a game and send the game setting to every registered agent, and start the inactivity timeout checker."""
        # assert that there is no competition running.
        assert not self.is_game_running()
        self.current_game = self._create_game()

        try:
            self.controller_agent.monitor.set_gamestats(GameStats(self.current_game))
            self.controller_agent.monitor.update()
        except Exception as e:
            logger.exception(e)

        self._send_game_data_to_agents()

        # log messages
        logger.debug("[{}]: Started competition:\n{}".format(self.controller_agent.name, self.current_game.get_holdings_summary()))
        logger.debug("[{}]: Computed equilibrium:\n{}".format(self.controller_agent.name, self.current_game.get_equilibrium_summary()))

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
                self.controller_agent.crypto,
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
                         .format(self.controller_agent.name, public_key, str(game_data_response)))

            self.game_data_per_participant[public_key] = game_data_response
            self.controller_agent.send_message(0, 1, public_key, game_data_response.serialize())

    def handle_registration_phase(self) -> bool:
        """
        Wait until the registration time expires. Then, if there are enough agents, start the competition.

        :return True if the competition has been successfully started. False otherwise.
        """
        # just to make names shorter
        min_nb_agents = self.tac_parameters.min_nb_agents

        seconds_to_wait = self.tac_parameters.registration_timedelta.seconds
        seconds_to_wait = 0 if seconds_to_wait < 0 else seconds_to_wait
        logger.debug("[{}]: Waiting for {} seconds...".format(self.controller_agent.name, seconds_to_wait))
        time.sleep(seconds_to_wait)
        nb_reg_agents = len(self.registered_agents)
        logger.debug("[{}]: Check if we can start the competition.".format(self.controller_agent.name))
        if len(self.registered_agents) >= self.tac_parameters.min_nb_agents:
            logger.debug("[{}]: Start competition. Registered agents: {}, minimum number of agents: {}."
                         .format(self.controller_agent.name, nb_reg_agents, min_nb_agents))
            self._start_competition()
            return True
        else:
            logger.debug("[{}]: Not enough agents to start TAC. Registered agents: {}, minimum number of agents: {}."
                         .format(self.controller_agent.name, nb_reg_agents, min_nb_agents))
            self.notify_tac_cancelled()
            self.controller_agent.terminate()
            return False

    def notify_tac_cancelled(self):
        """Notify agents that the TAC is cancelled."""
        for agent_pbk in self.registered_agents:
            self.controller_agent.send_message(0, 0, agent_pbk, Cancelled(agent_pbk, self.controller_agent.crypto).serialize())


class ControllerAgent(OEFAgent):
    """Class for a controller agent."""

    CONTROLLER_DATAMODEL = DataModel("tac", [
        AttributeSchema("version", int, True, "Version number of the TAC Controller Agent."),
    ])

    def __init__(self, name: str = "controller",
                 oef_addr: str = "127.0.0.1",
                 oef_port: int = 10000,
                 version: int = 1,
                 monitor: Optional[Monitor] = None,
                 **kwargs):
        """
        Initialize a Controller Agent for TAC.

        :param name: The name of the OEF Agent.
        :param oef_addr: the OEF address.
        :param oef_port: the OEF listening port.
        :param version: the version of the TAC controller.
        :param monitor: the GUI monitor. If None, defaults to a null (dummy) monitor.
        """
        self.name = name
        self.crypto = Crypto()
        super().__init__(self.crypto.public_key, oef_addr, oef_port, loop=asyncio.new_event_loop())
        logger.debug("[{}]: Initialized myself as Controller Agent :\n{}".format(self.name, pprint.pformat(vars())))

        self.dispatcher = ControllerDispatcher(self)
        self.monitor = NullMonitor() if monitor is None else monitor  # type: Monitor

        self.version = version
        self.game_handler = None  # type: Optional[GameHandler]

        self.last_activity = datetime.datetime.now()

        self._message_processing_task = None
        self._timeout_checker_task = None

        self._is_running = False
        self._terminated = False

    def on_message(self, msg_id: int, dialogue_id: int, origin: str, content: bytes) -> None:
        """
        Handle a simple message.

        The TAC Controller expects that 'content' is a Protobuf serialization of a tac.messages.Request object.
        The request is dispatched to the right request handler (using the ControllerHandler).
        The handler returns an optional response, that is sent back to the sender.
        Notice: the message sent back has the same message id, such that the client knows to which request the response is associated to.

        :param msg_id: the message id
        :param dialogue_id: the dialogue id
        :param origin: the public key of the sender.
        :param content: the content of the message.
        :return: None
        """
        logger.debug("[{}] on_message: msg_id={}, dialogue_id={}, origin={}"
                     .format(self.name, msg_id, dialogue_id, origin))
        self.update_last_activity()
        response = self.dispatcher.process_request(content, origin)  # type: Optional[Response]
        if response is not None:
            self.send_message(msg_id, dialogue_id, origin, response.serialize())

    def register(self):
        """
        Register on the OEF as a TAC controller agent.

        :return: None.
        """
        desc = Description({"version": 1}, data_model=self.CONTROLLER_DATAMODEL)
        logger.debug("[{}]: Registering with {} data model".format(self.name, desc.data_model.name))
        self.register_service(0, desc)

    def dump(self, directory: str, experiment_name: str) -> None:
        """
        Dump the details of the simulation.

        :param directory: the directory where experiments details are listed.
        :param experiment_name: the name of the folder where the data about experiment will be saved.
        :return: None.
        """
        experiment_dir = directory + "/" + experiment_name

        if self.game_handler is None or not self.game_handler.is_game_running():
            logger.warning("[{}]: Game not present. Using empty dictionary.".format(self.name))
            game_dict = {}  # type: Dict[str, Any]
        else:
            game_dict = self.game_handler.current_game.to_dict()

        os.makedirs(experiment_dir, exist_ok=True)
        with open(os.path.join(experiment_dir, "game.json"), "w") as f:
            json.dump(game_dict, f)

    def terminate(self) -> None:
        """
        Terminate the controller agent.

        :return: None
        """
        if self._is_running:
            logger.debug("[{}]: Terminating the controller...".format(self.name))
            self._is_running = False
            self.game_handler.notify_tac_cancelled()
            self._loop.call_soon_threadsafe(self.stop)
            if self.monitor.is_running: self.monitor.stop()
            self._message_processing_task.join()
            self._message_processing_task = None

    def check_inactivity_timeout(self, rate: Optional[float] = 2.0) -> None:
        """
        Check periodically if the timeout for inactivity or competition expired.

        :param: rate: at which rate (in seconds) the frequency of the check.
        :return: None
        """
        logger.debug("[{}]: Started job to check for inactivity of {} seconds. Checking rate: {}"
                     .format(self.name, self.game_handler.tac_parameters.inactivity_timedelta.total_seconds(), rate))
        while True:
            if self._is_running is False:
                return
            time.sleep(rate)
            current_time = datetime.datetime.now()
            inactivity_duration = current_time - self.last_activity
            if inactivity_duration > self.game_handler.tac_parameters.inactivity_timedelta:
                logger.debug("[{}]: Inactivity timeout expired. Terminating...".format(self.name))
                self.terminate()
                return
            elif current_time > self.game_handler.tac_parameters.end_time:
                logger.debug("[{}]: Competition timeout expired. Terminating...".format(self.name))
                self.terminate()
                return

    def update_last_activity(self):
        """Update the last activity tracker."""
        self.last_activity = datetime.datetime.now()

    def handle_competition(self, tac_parameters: TACParameters):
        """
        Start a Trading Agent Competition.

        :param tac_parameters: the parameter of the competition.
        :return:
        """
        logger.debug("[{}]: Starting competition with parameters: {}"
                     .format(self.name, pprint.pformat(tac_parameters.__dict__)))
        self._is_running = True
        self._message_processing_task = Thread(target=self.run)

        self.monitor.start(None)
        self.monitor.update()

        self.game_handler = GameHandler(self, tac_parameters)
        self._message_processing_task.start()

        if self.game_handler.handle_registration_phase():
            # start the inactivity timeout.
            self._timeout_checker_task = Thread(target=self.check_inactivity_timeout)
            self._timeout_checker_task.run()
        else:
            self.terminate()

    def wait_and_handle_competition(self, tac_parameters: TACParameters) -> None:
        """
        Wait until the current time is greater than the start time, then, start the TAC.

        :param tac_parameters: the parameters for TAC.
        :return: None
        """
        now = datetime.datetime.now()
        logger.debug("[{}]: waiting for starting the competition: start_time={}, current_time={}, timedelta ={}s"
                     .format(self.name, str(tac_parameters.start_time), str(now),
                             (tac_parameters.start_time - now).total_seconds()))

        seconds_to_wait = (tac_parameters.start_time - now).total_seconds()
        time.sleep(0.5 if seconds_to_wait < 0 else seconds_to_wait)
        self.handle_competition(tac_parameters)


def _parse_arguments():
    parser = argparse.ArgumentParser("controller", description="Launch the controller agent.")
    parser.add_argument("--name", default="controller", help="Name of the agent.")
    parser.add_argument("--nb-agents", default=5, type=int, help="Number of goods")
    parser.add_argument("--nb-goods", default=5, type=int, help="Number of goods")
    parser.add_argument("--money-endowment", type=int, default=200, help="Initial amount of money.")
    parser.add_argument("--base-good-endowment", default=2, type=int, help="The base amount of per good instances every agent receives.")
    parser.add_argument("--lower-bound-factor", default=0, type=int, help="The lower bound factor of a uniform distribution.")
    parser.add_argument("--upper-bound-factor", default=0, type=int, help="The upper bound factor of a uniform distribution.")
    parser.add_argument("--tx-fee", default=1.0, type=float, help="Number of goods")
    parser.add_argument("--oef-addr", default="127.0.0.1", help="TCP/IP address of the OEF Agent")
    parser.add_argument("--oef-port", default=10000, help="TCP/IP port of the OEF Agent")
    parser.add_argument("--start-time", default=str(datetime.datetime.now() + datetime.timedelta(0, 10)), type=str, help="The start time for the competition (in UTC format).")
    parser.add_argument("--registration-timeout", default=10, type=int, help="The amount of time (in seconds) to wait for agents to register before attempting to start the competition.")
    parser.add_argument("--inactivity-timeout", default=60, type=int, help="The amount of time (in seconds) to wait during inactivity until the termination of the competition.")
    parser.add_argument("--competition-timeout", default=240, type=int, help="The amount of time (in seconds) to wait from the start of the competition until the termination of the competition.")
    parser.add_argument("--whitelist-file", default=None, type=str, help="The file that contains the list of agent names to be whitelisted.")
    parser.add_argument("--verbose", default=False, action="store_true", help="Log debug messages.")
    parser.add_argument("--gui", action="store_true", help="Show the GUI.")
    parser.add_argument("--visdom-addr", default="localhost", help="TCP/IP address of the Visdom server.")
    parser.add_argument("--visdom-port", default=8097, help="TCP/IP port of the Visdom server.")
    parser.add_argument("--data-output-dir", default="data", help="The output directory for the simulation data.")
    parser.add_argument("--experiment-id", default=None, help="The experiment ID.")
    parser.add_argument("--seed", default=42, help="The random seed for the generation of the game parameters.")
    parser.add_argument("--version", default=1, help="The version of the controller.")

    return parser.parse_args()


def main(
        name: str = "controller",
        nb_agents: int = 5,
        nb_goods: int = 5,
        money_endowment: int = 200,
        base_good_endowment: int = 2,
        lower_bound_factor: int = 0,
        upper_bound_factor: int = 0,
        tx_fee: float = 1.0,
        oef_addr: str = "127.0.0.1",
        oef_port: int = 10000,
        start_time: str = str(datetime.datetime.now() + datetime.timedelta(0, 10)),
        registration_timeout: int = 10,
        inactivity_timeout: int = 60,
        competition_timeout: int = 240,
        whitelist_file: Optional[str] = None,
        verbose: bool = False,
        gui: bool = False,
        visdom_addr: str = "localhost",
        visdom_port: int = 8097,
        data_output_dir: str = "data",
        experiment_id: Optional[str] = None,
        seed: int = 42,
        version: int = 1,
        **kwargs
):
    """Run the controller script."""
    agent = None  # type: Optional[ControllerAgent]
    random.seed(seed)

    if verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    monitor = VisdomMonitor(visdom_addr=visdom_addr, visdom_port=visdom_port) if gui else NullMonitor()

    try:

        agent = ControllerAgent(name=name,
                                oef_addr=oef_addr,
                                oef_port=oef_port,
                                monitor=monitor,
                                version=version)

        whitelist = set(open(whitelist_file).read().splitlines(keepends=False)) if whitelist_file else None
        tac_parameters = TACParameters(
            min_nb_agents=nb_agents,
            money_endowment=money_endowment,
            nb_goods=nb_goods,
            tx_fee=tx_fee,
            base_good_endowment=base_good_endowment,
            lower_bound_factor=lower_bound_factor,
            upper_bound_factor=upper_bound_factor,
            start_time=dateutil.parser.parse(start_time),
            registration_timeout=registration_timeout,
            competition_timeout=competition_timeout,
            inactivity_timeout=inactivity_timeout,
            whitelist=whitelist
        )

        agent.connect()
        agent.register()
        agent.wait_and_handle_competition(tac_parameters)

    except Exception as e:
        logger.exception(e)
    except KeyboardInterrupt:
        logger.debug("Controller interrupted...")
    finally:
        if agent is not None:
            agent.terminate()
            experiment_name = experiment_id if experiment_id is not None else str(datetime.datetime.now()).replace(" ", "_")
            agent.dump(data_output_dir, experiment_name)
            if agent.game_handler is not None and agent.game_handler.is_game_running():
                game_stats = GameStats(agent.game_handler.current_game)
                game_stats.dump(data_output_dir, experiment_name)


if __name__ == '__main__':
    arguments = _parse_arguments()
    main(**arguments.__dict__)

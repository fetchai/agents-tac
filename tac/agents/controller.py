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

"""This module contains the classes that implements the Controller agent behaviour.
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
import time
from abc import ABC, abstractmethod
from threading import Thread
from typing import Dict, Type
from typing import Optional, Set

from oef.agents import OEFAgent
from oef.schema import Description, DataModel, AttributeSchema

from tac.game import Game, GameTransaction
from tac.gui.monitor import Monitor, NullMonitor
from tac.helpers.misc import generate_pbks
from tac.protocol import Response, Request, Register, Unregister, Error, GameData, \
    Transaction, TransactionConfirmation, ErrorCode, Cancelled
from tac.stats import GameStats

if __name__ != "__main__":
    logger = logging.getLogger(__name__)
else:
    logger = logging.getLogger("tac.agents.controller")


def parse_arguments():
    parser = argparse.ArgumentParser("controller", description="Launch the controller agent.")
    parser.add_argument("--public-key", default="controller", help="Public key of the agent.")
    parser.add_argument("--oef-addr", default="127.0.0.1", help="TCP/IP address of the OEF Agent")
    parser.add_argument("--oef-port", default=3333, help="TCP/IP port of the OEF Agent")
    parser.add_argument("--money", default=20, help="Money endowment for TAC agents.")
    parser.add_argument("--nb-agents", default=5, type=int, help="Number of goods")
    parser.add_argument("--nb-goods", default=5, type=int, help="Number of goods")
    parser.add_argument("--lower-bound-factor", default=1, type=int, help="The lower bound factor of a uniform distribution.")
    parser.add_argument("--upper-bound-factor", default=1, type=int, help="The upper bound factor of a uniform distribution.")
    parser.add_argument("--tx-fee", default=1, type=int, help="Number of goods")
    parser.add_argument("--inactivity-countdown", default=30, type=int, help="Timeout of inactivity.")
    parser.add_argument("--verbose", default=False, action="store_true", help="Log debug messages.")
    parser.add_argument("--gui", action="store_true", help="Show the GUI.")

    return parser.parse_args()


class TACParameters(object):

    def __init__(self, min_nb_agents: int = 5,
                 money_endowment: int = 200,
                 nb_goods: int = 5,
                 tx_fee: float = 1.0,
                 base_amount: int = 2,
                 lower_bound_factor: int = 1,
                 upper_bound_factor: int = 1,
                 start_time: datetime.datetime = None,
                 end_time: datetime.datetime = None,
                 inactivity_timeout: Optional[int] = None):
        """
        Initialize parameters for TAC
        :param min_nb_agents: the number of agents to wait for the registration.
        :param money_endowment: the initial amount of money to assign to every agent.
        :param nb_goods: the number of goods in the competition.
        :param tx_fee: the fee for a transaction.
        :param base_amount: the base amount of instances per good
        :param lower_bound_factor: the lower bound factor of a uniform distribution.
        :param upper_bound_factor: the upper bound factor of a uniform distribution.
        :param start_time: the time when the competition will start.
        :param end_time: the time when the competition will end.
        :param inactivity_timeout: the time when the competition will start.
        """
        self._min_nb_agents = min_nb_agents
        self._money_endowment = money_endowment
        self._nb_goods = nb_goods
        self._tx_fee = tx_fee
        self._base_amount = base_amount
        self._lower_bound_factor = lower_bound_factor
        self._upper_bound_factor = upper_bound_factor
        self._start_time = start_time
        self._end_time = end_time
        self._inactivity_timeout = inactivity_timeout

    @property
    def min_nb_agents(self) -> int:
        return self._min_nb_agents

    @property
    def money_endowment(self):
        return self._money_endowment

    @property
    def nb_goods(self):
        return self._nb_goods

    @property
    def tx_fee(self):
        return self._tx_fee

    @property
    def base_amount(self):
        return self._base_amount

    @property
    def lower_bound_factor(self):
        return self._lower_bound_factor

    @property
    def upper_bound_factor(self):
        return self._upper_bound_factor

    @property
    def start_time(self):
        return self._start_time

    @property
    def end_time(self):
        return self._end_time

    @property
    def inactivity_timeout(self):
        return self._inactivity_timeout


class RequestHandler(ABC):

    def __init__(self, controller_agent: 'ControllerAgent'):
        self.controller_agent = controller_agent

    def __call__(self, request: Request) -> Response:
        return self.handle(request)

    @abstractmethod
    def handle(self, request: Request) -> Optional[Response]:
        """
        Handle a request from an OEF agent. It returns
        :param request: the request message.
        :return: a response, or None.
        """


class RegisterHandler(RequestHandler):

    def handle(self, request: Request) -> Optional[Response]:
        """
        Handle a register message.
        If the public key is already registered, answer with an error message.
        If this is the n_th registration request, where n is equal to nb_agents, then start the competition.

        :param request: the register request.
        :return: an Error response if an error occurred, else None.
        """
        if request.public_key in self.controller_agent.game_handler.registered_agents:
            error_msg = "Agent already registered: '{}'".format(request.public_key)
            logger.error(error_msg)
            return Error(request.public_key, ErrorCode.AGENT_ALREADY_REGISTERED)
        else:
            logger.debug("Agent registered: '{}'".format(request.public_key))
            self.controller_agent.game_handler.registered_agents.add(request.public_key)
            return None


class UnregisterHandler(RequestHandler):

    def handle(self, request: Request) -> Optional[Response]:
        """
        Handle a unregister message.
        If the public key is not registered, answer with an error message.

        :param request: the register request.
        :return: an Error response if an error occurred, else None.
        """
        if request.public_key not in self.controller_agent.game_handler.registered_agents:
            error_msg = "Agent not registered: '{}'".format(request.public_key)
            logger.error(error_msg)
            return Error(request.public_key, ErrorCode.AGENT_NOT_REGISTERED)
        else:
            logger.debug("Agent unregistered: '{}'".format(request.public_key))
            self.controller_agent.game_handler.registered_agents.remove(request.public_key)
            return None


class TransactionHandler(RequestHandler):

    def __init__(self, controller_agent: 'ControllerAgent'):
        super().__init__(controller_agent)
        self._pending_transaction_requests = {}  # type: Dict[str, Transaction]

    def handle(self, request: Transaction) -> Optional[Response]:
        """
        Handle a transaction request message.
        If the transaction is invalid (e.g. because the state of the game are not consistent), reply with an error.

        :param request: the transaction request.
        :return: an Error response if an error occurred, else None (no response to send back).
        """
        logger.debug("Handling transaction: {}".format(request))

        # if transaction arrives first time then put it into the pending pool
        if request.transaction_id not in self._pending_transaction_requests:
            logger.debug("Put transaction request in the pool: {}".format(request.transaction_id))
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
                    return self._handle_valid_transaction(request)
                else:
                    return self._handle_invalid_transaction(request)
            else:
                return self._handle_non_matching_transaction(request)

    def _handle_valid_transaction(self, request: Transaction) -> None:
        """
        Handle a valid transaction. That is:
        - update the game state
        - send a transaction confirmation both to the buyer and the seller.
        :param request: the transaction request.
        :return: None
        """
        logger.debug("Handling valid transaction: {}".format(request.transaction_id))

        # update the game state.
        tx = self.controller_agent.game_handler.from_request_to_game_tx(request)
        self.controller_agent.game_handler.current_game.settle_transaction(tx)
        self.controller_agent.monitor.update()

        # send the transaction confirmation.
        tx_confirmation = TransactionConfirmation(request.public_key, request.transaction_id)
        self.controller_agent.send_message(0, 0, request.public_key, tx_confirmation.serialize())
        self.controller_agent.send_message(0, 0, request.counterparty, tx_confirmation.serialize())

        # log messages
        logger.debug("[Controller]: Transaction '{}' settled successfully.".format(request.transaction_id))
        holdings_summary = self.controller_agent.game_handler.current_game.get_holdings_summary()
        logger.debug("[Controller]: Current state:\n{}".format(holdings_summary))

        return None

    def _handle_invalid_transaction(self, request: Transaction) -> Response:
        """Handle an invalid transaction."""
        return Error(request.public_key, ErrorCode.TRANSACTION_NOT_VALID, {"transaction_id": request.transaction_id})

    def _handle_non_matching_transaction(self, request: Transaction) -> Response:
        """Handle non-matching transaction."""
        return Error(request.public_key, ErrorCode.TRANSACTION_NOT_MATCHING)


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
            Transaction: TransactionHandler(controller_agent)
        }  # type: Dict[Type[Request], RequestHandler]

    def register_handler(self, request_type: Type[Request], request_handler: RequestHandler) -> None:
        self.handlers[request_type] = request_handler

    def process_request(self, msg: bytes, public_key: str) -> Response:
        """Handle a simple message coming from an agent.
        :param msg: the Protobuf message.
        :param public_key: the agent's public key that sent the request.
        :return: the Response object
        """
        message = self.decode(msg, public_key)  # type: Request
        response = self.dispatch(message)
        logger.debug("[{}]: Returning response: {}".format(self.controller_agent.public_key, str(response)))
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
            return Error(request.public_key, ErrorCode.REQUEST_NOT_VALID)
        try:
            return handle_request(request)
        except Exception as e:
            return Error(request.public_key, ErrorCode.GENERIC_ERROR)

    def decode(self, msg: bytes, public_key: str) -> Request:
        """
        From bytes to a Request message
        :param msg: the serialized message.
        :param public_key: the public key of the sender agent.
        :return: the deserialized Request
        """
        request = Request.from_pb(msg, public_key)
        return request


class GameHandler:
    """
    A class to manage a TAC instance.
    """

    def __init__(self, controller_agent: 'ControllerAgent', tac_parameters: TACParameters):
        """
        :param controller_agent: the controller agent the handler is associated with.
        """
        self.controller_agent = controller_agent
        self.tac_parameters = tac_parameters

        self.registered_agents = set()  # type: Set[str]
        self.current_game = None  # type: Optional[Game]
        self.inactivity_timeout_timedelta = datetime.timedelta(seconds=tac_parameters.inactivity_timeout) \
            if tac_parameters.inactivity_timeout is not None else datetime.timedelta(seconds=15)

    def reset(self) -> None:
        """Reset the game."""
        self.current_game = None
        self.registered_agents = set()

    def is_game_running(self) -> bool:
        """
        Check if an instance of a game is already set up.
        :return: Return True if there is a game running, False otherwise.
        """
        return self.current_game is not None

    def from_request_to_game_tx(self, transaction: Transaction) -> GameTransaction:
        """
        From a transaction request message to a game transaction
        :param transaction: the request message for a transaction.
        :return: the game transaction.
        """
        sender_pbk = transaction.sender
        receiver_pbk = transaction.counterparty
        buyer_pbk, seller_pbk = (sender_pbk, receiver_pbk) if transaction.buyer else (receiver_pbk, sender_pbk)

        tx = GameTransaction(
            buyer_pbk,
            seller_pbk,
            transaction.amount,
            transaction.quantities_by_good_pbk
        )
        return tx

    def _start_competition(self):
        """Create a game and send the game setting to every registered agent.
        Moreover, start the inactivity timeout checker."""
        # assert that there is no competition running.
        assert not self.is_game_running()
        self.current_game = self._create_game()
        self.controller_agent.monitor.start(GameStats(self.current_game))
        self.controller_agent.monitor.update()
        self._send_game_data_to_agents()

        # start the inactivity timeout.
        self._timeout_checker_task = Thread(target=self.controller_agent.check_inactivity_timeout)
        self._timeout_checker_task.start()

        # log messages
        logger.debug("Started competition:\n{}".format(self.current_game.get_holdings_summary()))
        logger.debug("Computed equilibrium:\n{}".format(self.current_game.get_equilibrium_summary()))

    def _create_game(self) -> Game:
        """
        Create a TAC game.
        In particular:
        - take the number of goods and generate a set of score values {0, 1, 2, ..., nb_goods}
        - use the public keys as labels for the agents in the game.
        - use the same money amount for every agent.

        :return: a Game instance.
        """
        agent_pbks = sorted(self.registered_agents)
        nb_agents = len(agent_pbks)
        good_pbks = generate_pbks(self.controller_agent.game_handler.tac_parameters.nb_goods, 'good')

        game = Game.generate_game(nb_agents,
                                  self.tac_parameters.nb_goods,
                                  self.tac_parameters.money_endowment,
                                  self.tac_parameters.tx_fee,
                                  self.tac_parameters.base_amount,
                                  self.tac_parameters.lower_bound_factor,
                                  self.tac_parameters.upper_bound_factor,
                                  agent_pbks,
                                  good_pbks)
        return game

    def _send_game_data_to_agents(self) -> None:
        """
        Send the data of every agent about the game (e.g. endowments, preferences, scores)
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
                self.current_game.configuration.agent_pbks,
                self.current_game.configuration.good_pbks
            )
            logger.debug("[{}]: sending GameData to '{}': {}"
                         .format(self.controller_agent.public_key, public_key, str(game_data_response)))
            self.controller_agent.send_message(0, 1, public_key, game_data_response.serialize())

    def handle_registration_phase(self) -> bool:
        """Wait until the registration time expires. Then, if there are enough agents, start the competition.

        :return True if the competition has been successfully started. False otherwise.
        """
        # just to make names shorter
        ctrl_pbk = self.controller_agent.public_key
        nb_reg_agents = len(self.registered_agents)
        min_nb_agents = self.tac_parameters.min_nb_agents

        seconds_to_wait = (self.tac_parameters.start_time - datetime.datetime.now()).seconds + 1
        seconds_to_wait = 0 if seconds_to_wait < 0 else seconds_to_wait
        logger.debug("[{}]: Waiting for {} seconds...".format(ctrl_pbk, seconds_to_wait))
        time.sleep(seconds_to_wait)
        logger.debug("[Controller]: Check if we can start the competition.".format(seconds_to_wait))
        if len(self.registered_agents) >= self.tac_parameters.min_nb_agents:
            logger.debug("[{}]: Start competition. Registered agents: {}, minimum number of agents: {}."
                         .format(ctrl_pbk, nb_reg_agents, min_nb_agents))
            self._start_competition()
            return True
        else:
            logger.debug("[{}]: Not enough agents to start TAC. Registered agents: {}, minimum number of agents: {}."
                         .format(ctrl_pbk, nb_reg_agents, min_nb_agents))
            self.notify_tac_cancelled()
            self.controller_agent.terminate()
            return False

    def notify_tac_cancelled(self):
        for tac_agent in self.registered_agents:
            self.controller_agent.send_message(0, 0, tac_agent, Cancelled(tac_agent).serialize())


class ControllerAgent(OEFAgent):
    CONTROLLER_DATAMODEL = DataModel("tac", [
        AttributeSchema("version", int, True, "Version number of the TAC Controller Agent."),
    ])
    # TODO need at least one attribute in the search Query to the OEF.

    def __init__(self, public_key: str = "controller",
                 oef_addr: str = "127.0.0.1",
                 oef_port: int = 3333,
                 version: int = 1,
                 monitor: Optional[Monitor] = None,
                 **kwargs):
        """
        Initialize a Controller Agent for TAC.
        :param public_key: The public key of the OEF Agent.
        :param oef_addr: the OEF address.
        :param oef_port: the OEF listening port.
        :param monitor: the GUI monitor. If None, defaults to a null (dummy) monitor.
        :param gui: show the GUI.
        """
        super().__init__(public_key, oef_addr, oef_port, loop=asyncio.new_event_loop())
        logger.debug("Initialized Controller Agent :\n{}".format(pprint.pformat(vars())))

        self.dispatcher = ControllerDispatcher(self)
        self.monitor = NullMonitor() if monitor is None else monitor  # type: Monitor
        self.version = version
        self.game_handler = None  # type: Optional[GameHandler]

        self.last_activity = datetime.datetime.now()

        self._message_processing_task = None
        self._timeout_checker_task = None

        self._is_running = False

    def on_message(self, msg_id: int, dialogue_id: int, origin: str, content: bytes) -> None:
        """
        Handle a simple message.
        The TAC Controller expects that 'content' is a Protobuf serialization of a tac.messages.Request object.
        The request is dispatched to the right request handler (using the ControllerHandler).
        The handler returns an optional response, that is sent back to the sender.
        Notice: the message sent back has the same message id, such that the client knows to which request
                the response is associated to.

        :param msg_id: the message id
        :param dialogue_id: the dialogue id
        :param origin: the public key of the sender.
        :param content: the content of the message.
        :return: None
        """
        logger.debug("[ControllerAgent] on_message: msg_id={}, dialogue_id={}, origin={}"
                     .format(msg_id, dialogue_id, origin))
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
        logger.debug("Registering with {} data model".format(desc.data_model.name))
        self.register_service(0, desc)

    def dump(self, directory: str, experiment_name: str) -> None:
        """
        Dump the details of the simulation.

        :param directory: the directory where experiments details are listed.
        :param experiment_name: the name of the folder where the data about experiment will be saved.
        :return: None.
        """
        experiment_dir = directory + "/" + experiment_name

        if not self.game_handler.is_game_running():
            logger.warning("Game not present. Using empty dictionary.")
            game_dict = {}
        else:
            game_dict = self.game_handler.current_game.to_dict()

        os.makedirs(experiment_dir, exist_ok=True)
        with open(os.path.join(experiment_dir, "game.json"), "w") as f:
            json.dump(game_dict, f)

    def terminate(self) -> None:
        """
        Terminate the controller agent
        :return: None
        """
        logger.debug("[{}]: Terminating the controller...".format(self.public_key))
        self._is_running = False
        self.game_handler.notify_tac_cancelled()
        self._loop.call_soon_threadsafe(self._task.cancel)
        self.monitor.stop()
        self._message_processing_task.join()
        self._message_processing_task = None

    def check_inactivity_timeout(self, rate: Optional[float] = 2.0) -> None:
        """
        Check periodically if the timeout for inactivity or competition expired.
        :param: rate: at which rate (in seconds) the frequency of the check.
        :return: None
        """
        logger.debug("Started job to check for inactivity of {} seconds. Checking rate: {}"
                     .format(self.game_handler.inactivity_timeout_timedelta.total_seconds(), rate))
        while True:
            if self._is_running is False:
                return
            time.sleep(rate)
            current_time = datetime.datetime.now()
            inactivity_duration = current_time - self.last_activity
            if inactivity_duration > self.game_handler.inactivity_timeout_timedelta:
                logger.debug("[{}]: Inactivity timeout expired. Terminating...".format(self.public_key))
                self.terminate()
                return
            elif current_time > self.game_handler.tac_parameters.end_time:
                logger.debug("[{}]: Competition timeout expired. Terminating...".format(self.public_key))
                self.terminate()
                return

    def update_last_activity(self):
        self.last_activity = datetime.datetime.now()

    def start_competition(self, tac_parameters: TACParameters):
        """
        Start a Trading Agent Competition.
        :param tac_parameters: the parameter of the competition.
        :return:
        """
        self._is_running = True
        self._message_processing_task = Thread(target=self.run)
        self._message_processing_task.start()

        self.game_handler = GameHandler(self, tac_parameters)
        self.game_handler.handle_registration_phase()


def main():
    args = parse_arguments()

    if args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    try:
        agent = ControllerAgent(public_key=args.public_key,
                                oef_addr=args.oef_addr,
                                oef_port=args.oef_port,
                                min_nb_agents=args.nb_agents,
                                money_endowment=args.money_endowment,
                                nb_goods=args.nb_goods,
                                tx_fee=args.tx_fee,
                                lower_bound_factor=args.lower_bound_factor,
                                upper_bound_factor=args.upper_bound_factor,
                                version=args.version,
                                start_time=args.start_time,
                                end_time=args.end_time,
                                inactivity_timeout=args.inactivity_timeout,
                                gui=args.gui)

        agent.connect()
        agent.register()

        agent.run_controller()

    finally:
        agent.terminate()


if __name__ == '__main__':
    main()

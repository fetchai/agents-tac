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
import datetime
import json
import logging
import os
import pprint
import time
from typing import Optional, Set

from oef.schema import DataModel, Description, AttributeSchema

from tac.core import TACAgent
from tac.game import Game, GameTransaction
from tac.helpers.plantuml import plantuml_gen
from tac.protocol import Response, Request, Register, Unregister, Error, GameData, \
    Transaction, TransactionConfirmation

logger = logging.getLogger(__name__)


def parse_arguments():
    parser = argparse.ArgumentParser("controller", description="Launch the controller agent.")
    parser.add_argument("--public-key", default="controller", help="Public key of the agent.")
    parser.add_argument("--oef-addr", default="127.0.0.1", help="TCP/IP address of the OEF Agent")
    parser.add_argument("--oef-port", default=3333, help="TCP/IP port of the OEF Agent")
    parser.add_argument("--money",    default=20,   help="Money endowment for TAC agents.")
    parser.add_argument("--nb-agents", default=5, type=int, help="Number of goods")
    parser.add_argument("--nb-goods", default=5, type=int, help="Number of goods")
    parser.add_argument("--lower-bound-factor", default=1, type=int, help="The lower bound factor of a uniform distribution.")
    parser.add_argument("--upper-bound-factor", default=1, type=int, help="The upper bound factor of a uniform distribution.")
    parser.add_argument("--fee", default=1, type=int, help="Number of goods")
    # parser.add_argument("--gui", action="store_true", help="Show the GUI.")

    return parser.parse_args()


class ControllerHandler(object):
    """Class to wrap the decoding procedure and dispatching the handling of the message to the right function."""

    def __init__(self, controller_agent: 'ControllerAgent'):
        """
        Initialize a Controller handler, i.e. the class that manages the handling of incoming messages.

        :param controller_agent: The Controller Agent the handler is associated with.
        """
        self.controller_agent = controller_agent
        self.game_handler = controller_agent.game_handler

    def handle(self, msg: bytes, public_key: str) -> Response:
        """Handle a simple message coming from an agent.
        :param msg: the Protobuf message.
        :param public_key: the agent's public key that sent the request.
        :return: the Response object
        """
        message = self.decode(msg, public_key)  # type: Request
        response = self.dispatch(message, public_key)
        logger.debug("[{}]: Returning response: {}".format(self.controller_agent.public_key, str(response)))
        return response

    def dispatch(self, request: Request, public_key: str) -> Response:
        """
        Dispatch the request to the right handler.

        :param request: the request to handle
        :param public_key: the public key of the sender agent.
        :return: the response.
        """
        try:
            if isinstance(request, Register):
                return self.handle_register(request, public_key)
            elif isinstance(request, Unregister):
                return self.handle_unregister(request, public_key)
            elif isinstance(request, Transaction):
                return self.handle_transaction(request, public_key)
            else:
                error_msg = "Request not recognized"
                logger.error(error_msg)
                return Error(error_msg)
        except Exception as e:
            error_msg = "Unexpected error."
            logger.exception(error_msg)
            return Error(error_msg)

    def decode(self, msg: bytes, public_key: str) -> Request:
        """From bytes to a Response message"""
        request = Request.from_pb(msg)
        return request

    def handle_register(self, request: Register, public_key: str) -> Optional[Response]:
        """
        Handle a register message.
        If the public key is already registered, answer with an error message.
        If this is the n_th registration request, where n is equal to nb_agents, then start the competition.

        :param request: the register request.
        :param public_key: the public key of the sender agent.
        :return: an Error response if an error occurred, else None.
        """
        if public_key in self.controller_agent.game_handler.registered_agents:
            error_msg = "Agent already registered: '{}'".format(public_key)
            logger.error(error_msg)
            return Error(error_msg)
        else:
            logger.debug("Agent registered: '{}'".format(public_key))
            self.controller_agent.game_handler.registered_agents.add(public_key)
            return None

    def handle_unregister(self, request: Unregister, public_key: str) -> Optional[Response]:
        """
        Handle a unregister message.
        If the public key is not registered, answer with an error message.

        :param request: the register request.
        :param public_key: the public key of the sender agent.
        :return: an Error response if an error occurred, else None.
        """
        if public_key not in self.controller_agent.game_handler.registered_agents:
            error_msg = "Agent not registered: '{}'".format(public_key)
            logger.error(error_msg)
            return Error(error_msg)
        else:
            logger.debug("Agent unregistered: '{}'".format(public_key))
            self.controller_agent.game_handler.registered_agents.remove(public_key)
            return None

    def handle_transaction(self, request: Transaction, public_key: str) -> Optional[Response]:
        """
        Handle a transaction request message.
        If the transaction is invalid (e.g. because the state of the game are not consistent), reply with an error.

        :param request: the transaction request.
        :param public_key: the public key of the sender agent.
        :return: an Error response if an error occurred, else None (no response to send back).
        """
        logger.debug("Handling transaction: {}".format(request))
        tx = self.game_handler.from_request_to_game_tx(request, public_key)
        if self.game_handler.current_game.is_transaction_valid(tx):
            return self._handle_valid_transaction(request, public_key)
        else:
            return self._handle_invalid_transaction()

    def _handle_valid_transaction(self, request: Transaction, public_key: str) -> None:
        """
        Handle a valid transaction. That is:
        - update the game state
        - send a transaction confirmation both to the buyer and the seller.
        :param request: the transaction request.
        :param public_key: the public key of the sender.
        :return: None
        """

        # update the game state.
        tx = self.game_handler.from_request_to_game_tx(request, public_key)
        self.game_handler.current_game.settle_transaction(tx)

        # send the transaction confirmation.
        tx_confirmation = TransactionConfirmation(request.transaction_id)
        self.controller_agent.send_message(0, 0, public_key, tx_confirmation.serialize())
        self.controller_agent.send_message(0, 0, request.counterparty, tx_confirmation.serialize())

        # log messages
        logger.debug("[Controller]: Transaction '{}' settled successfully.".format(request.transaction_id))
        holdings_summary = self.controller_agent.game_handler.current_game.get_holdings_summary()
        logger.debug("[Controller]: Current state:\n{}".format(holdings_summary))

        return None

    def _handle_invalid_transaction(self) -> Response:
        """Handle an invalid transaction."""
        return Error("Error in checking transaction.")


class GameHandler:
    """
    A class to manage a TAC instance.
    """

    def __init__(self, controller_agent: 'ControllerAgent',
                 min_nb_agents: int,
                 money_endowment: int,
                 nb_goods: int,
                 fee: int,
                 lower_bound_factor: int,
                 upper_bound_factor: int,
                 start_time: datetime.datetime = None):
        """
        :param controller_agent: the controller agent the handler is associated with.
        :param min_nb_agents: the number of agents to wait for during registration and before starting the game.
        :param money_endowment: the initial amount of money to assign to every agent.
        :param nb_goods: the number of goods in the competition.
        :param fee: the fee for a transaction.
        :param lower_bound_factor: the lower bound factor of a uniform distribution.
        :param upper_bound_factor: the upper bound factor of a uniform distribution.
        :param start_time: the time when the competition will start.
        """
        self.controller_agent = controller_agent
        self.min_nb_agents = min_nb_agents
        self.money_endowment = money_endowment
        self.nb_goods = nb_goods
        self.fee = fee
        self.lower_bound_factor = lower_bound_factor
        self.upper_bound_factor = upper_bound_factor
        self.start_time = start_time if start_time is not None else datetime.datetime.now() + datetime.timedelta(0, 5)

        self.registered_agents = set()  # type: Set[str]
        self.current_game = None  # type: Optional[Game]

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

    def from_request_to_game_tx(self, transaction: Transaction, agent_label: str) -> GameTransaction:
        """
        From a transaction request message to a game transaction
        :param transaction: the request message for a transaction.
        :param agent_label: the agent label that sent the transaction.
        :return: the game transaction.
        """
        sender_id = self.controller_agent.game_handler.current_game.configuration.agent_id_from_label(agent_label)
        receiver_id = self.current_game.agent_id_from_label(transaction.counterparty)
        buyer_id, seller_id = (sender_id, receiver_id) if transaction.buyer else (receiver_id, sender_id)

        tx = GameTransaction(
            buyer_id,
            seller_id,
            transaction.amount,
            transaction.quantities_by_good_id
        )
        return tx

    def _start_competition(self):
        """Create a game and send the game setting to every registered agent."""
        # assert that there is no competition running.
        assert not self.is_game_running()
        self.current_game = self._create_game()
        self._send_game_data_to_agents()

        # log messages
        logger.debug("Started competition:\n{}".format(self.current_game.get_holdings_summary()))
        plantuml_gen.start_competition(self.controller_agent.public_key, self.current_game)

    def _create_game(self) -> Game:
        """
        Create a TAC game.
        In particular:
        - take the number of goods and generate a set of score values {0, 1, 2, ..., nb_goods}
        - use the public keys as labels for the agents in the game.
        - use the same money amount for every agent.

        :return: a Game instance.
        """
        agents_ids = sorted(self.registered_agents)
        nb_agents = len(agents_ids)
        game = Game.generate_game(nb_agents, self.nb_goods, self.money_endowment, self.fee, self.lower_bound_factor, self.upper_bound_factor, agent_ids=agents_ids)
        return game

    def _send_game_data_to_agents(self) -> None:
        """
        Send the data of every agent about the game (e.g. endowments, preferences, scores)
        Assuming that the agent labels are public keys of the OEF Agents.

        :return: None.
        """
        for public_key in self.current_game.configuration.agent_labels:
            game_data = self.current_game.get_agent_state_from_agent_label(public_key)
            game_data_response = GameData(
                game_data.balance,
                game_data.current_holdings,
                game_data.utilities,
                self.fee,
            )
            logger.debug("[{}]: sending GameData to '{}': {}"
                         .format(self.controller_agent.public_key, public_key, str(game_data_response)))
            self.controller_agent.send_message(0, 1, public_key, game_data_response.serialize())

    def timeout_competition(self) -> bool:
        """Wait until the registration time expires. Then, if there are enough agents, start the competition.

        :return True if the competition has been successfully started. False otherwise.
        """

        seconds_to_wait = (self.start_time - datetime.datetime.now()).seconds + 1
        seconds_to_wait = 0 if seconds_to_wait < 0 else seconds_to_wait
        logger.debug("[{}]: Waiting for {} seconds...".format(self.controller_agent.public_key, seconds_to_wait))
        time.sleep(seconds_to_wait)
        logger.debug("[Controller]: Check if we can start the competition.".format(seconds_to_wait))
        if len(self.registered_agents) >= self.min_nb_agents:
            logger.debug("[{}]: Start competition. Registered agents: {}, minimum number of agents: {}."
                         .format(self.controller_agent.public_key, len(self.registered_agents), self.min_nb_agents))
            self._start_competition()
            return True
        else:
            logger.debug("[{}]: Not enough agents to start TAC. Registered agents: {}, minimum number of agents: {}."
                         .format(self.controller_agent.public_key, len(self.registered_agents), self.min_nb_agents))
            return False


class ControllerAgent(TACAgent):
    CONTROLLER_DATAMODEL = DataModel("tac", [
        AttributeSchema("version", int, True, "Version number of the TAC Controller Agent."),
    ])
    # TODO need at least one attribute in the search Query to the OEF.

    def __init__(self, public_key="controller", oef_addr="127.0.0.1", oef_port=3333,
                 min_nb_agents: int = 5, money_endowment: int = 20, nb_goods: int = 5,
                 fee: int = 1, lower_bound_factor: int = 1, upper_bound_factor: int = 1,
                 version: int = 1, start_time: datetime.datetime = None, **kwargs):
        """
        Initialize a Controller Agent for TAC.
        :param public_key: The public key of the OEF Agent.
        :param oef_addr: the OEF address.
        :param oef_port: the OEF listening port.
        :param min_nb_agents: the number of agents to wait for the registration.
        :param money_endowment: the initial amount of money to assign to every agent.
        :param nb_goods: the number of goods in the competition.
        :param fee: the fee for a transaction.
        :param lower_bound_factor: the lower bound factor of a uniform distribution.
        :param upper_bound_factor: the upper bound factor of a uniform distribution.
        :param version: the version of the TAC controller.
        :param start_time: the time when the competition will start.
        """
        super().__init__(public_key, oef_addr, oef_port, **kwargs)
        logger.debug("Initialized Controller Agent :\n{}".format(pprint.pformat({
            "public_key": public_key,
            "oef_addr": oef_addr,
            "oef_port": oef_port,
            "min_nb_agents": min_nb_agents,
            "money_endowment": money_endowment,
            "nb_goods": nb_goods,
            "fee": fee,
            "lower_bound_factor": lower_bound_factor,
            "upper_bound_factor": upper_bound_factor,
            "version": version,
            "start_time": str(start_time)
        })))

        self.game_handler = GameHandler(self, min_nb_agents, money_endowment, nb_goods, fee, lower_bound_factor, upper_bound_factor, start_time)
        self.handler = ControllerHandler(self)
        self.version = version

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
        response = self.handler.handle(content, origin)  # type: Optional[Response]
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

    def dump(self, directory: str = "data", experiment_name: Optional[str] = None) -> None:
        """
        Dump the details of the simulation.

        :param directory: the directory where experiments details are listed.
        :param experiment_name: the name of the folder where the data about experiment will be saved.
        :return: None.
        """
        experiment_name = experiment_name if experiment_name is not None else str(datetime.datetime.now()).replace(" ", "_")
        experiment_dir = directory + "/" + experiment_name

        if not self.game_handler.is_game_running():
            logger.warning("Game not present. Using empty dictionary.")
            game_dict = {}
        else:
            game_dict = self.game_handler.current_game.to_dict()

        os.makedirs(experiment_dir, exist_ok=True)
        with open(os.path.join(experiment_dir, "game.json"), "w") as f:
            json.dump(game_dict, f)


def main():
    args = parse_arguments()
    agent = ControllerAgent(public_key=args.public_key, oef_addr=args.oef_addr, oef_port=args.oef_port)

    agent.connect()
    agent.register()

    logger.debug("Running TAC dontroller agent...")
    agent.run()


if __name__ == '__main__':
    main()


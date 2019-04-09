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

import argparse
import asyncio
import datetime
import json
import logging
import os
import pprint
from typing import Optional, Set, Dict, List

from oef.schema import DataModel, Description, AttributeSchema

from tac.core import TacAgent, Game, GameTransaction
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
    parser.add_argument("--fee", default=1, type=int, help="Number of goods")
    # parser.add_argument("--gui", action="store_true", help="Show the GUI.")

    return parser.parse_args()


class ControllerHandler(object):
    """Class to wrap the decoding procedure and dispatching the handling of the message to the right function."""

    def __init__(self, controller: 'ControllerAgent'):
        """
        Initialize a Controller handler, i.e. the class that manages the handling of incoming messages.
        :param controller: The Controller Agent the handler is associated to.
        """
        self.controller = controller

    def handle(self, msg: bytes, public_key: str) -> Response:
        """Handle a simple message coming from an agent.
        :param msg: the Protobuf message.
        :param public_key: the agent's public key that sent the request.
        :return: the Response object
        """
        message = self.decode(msg, public_key)  # type: Request
        response = self.dispatch(message)
        logger.debug("[{}]: Returning response: {}".format(self.controller.public_key, str(response)))
        return response

    def dispatch(self, request: Request) -> Response:
        """
        Dispatch the request to the right handler.

        :param request: the request to handle
        :return: the response.
        """
        try:
            if isinstance(request, Register):
                return self.controller.handle_register(request)
            elif isinstance(request, Unregister):
                return self.controller.handle_unregister(request)
            elif isinstance(request, Transaction):
                return self.controller.handle_transaction(request)
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
        request = Request.from_pb(msg, public_key)
        return request


class ControllerAgent(TacAgent):
    CONTROLLER_DATAMODEL = DataModel("tac", [
        AttributeSchema("version", int, True, "Version number of the TAC Controller Agent."),
    ])
    # TODO need at least one attribute in the search Query to the OEF.

    def __init__(self, public_key="controller", oef_addr="127.0.0.1", oef_port=3333,
                 nb_agents: int = 5, money_endowment: int = 20, nb_goods: int = 5,
                 fee: int = 1, version: int = 1, start_time: datetime.datetime = None, **kwargs):
        """
        Initialize a Controller Agent for TAC.
        :param public_key: The public key of the OEF Agent.
        :param oef_addr: the OEF address.
        :param oef_port: the OEF listening port.
        :param nb_agents: the number of agents to wait for the registration.
        :param money_endowment: the initial amount of money to assign to every agent.
        :param nb_goods: the number of goods in the competition.
        :param fee: the fee for a transaction.
        :param version: the version of the TAC controller.
        :param start_time: the time when the competition will start.
        """
        super().__init__(public_key, oef_addr, oef_port, **kwargs)
        logger.debug("Initialized Controller Agent :\n{}".format(pprint.pformat({
            "public_key": public_key,
            "oef_addr": oef_addr,
            "oef_port": oef_port,
            "nb_agents": nb_agents,
            "money_endowment": money_endowment,
            "nb_goods": nb_goods,
            "fee": fee,
            "version": version,
            "start_time": str(start_time)
        })))

        self.nb_agents = nb_agents
        self.money_endowment = money_endowment
        self.nb_goods = nb_goods
        self.fee = fee
        self.version = version
        self.start_time = start_time

        self.registered_agents = set()  # type: Set[str]
        self.handler = ControllerHandler(self)

        self._current_game = None  # type: Optional[Game]
        self._agent_pbk_to_id = None  # type: Optional[Dict[str, int]]
        self._transaction_history = []  # type: List[Transaction]

        # TODO: assuming that somewhere else the agent loop is running...
        self._timeout_task = asyncio.ensure_future(self.timeout_competition(), loop=self._loop)

    async def timeout_competition(self) -> bool:
        """Wait until the registration time expires.
        Then, if there are enough agents, start the competition.

        :return True if
        """

        seconds_to_wait = (self.start_time - datetime.datetime.now()).seconds + 1
        seconds_to_wait = 0 if seconds_to_wait < 0 else seconds_to_wait
        logger.debug("[{}]: Waiting for {} seconds...".format(self.public_key, seconds_to_wait))
        await asyncio.sleep(seconds_to_wait)
        logger.debug("[{}]: Check if we can start the competition.".format(self.public_key, seconds_to_wait))
        if len(self.registered_agents) >= self.nb_agents:
            logger.debug("[{}]: Start competition. Registered agents: {}, minimum number of agents: {}."
                         .format(self.public_key, len(self.registered_agents), self.nb_agents))
            self._start_competition()
            return True
        else:
            logger.debug("[{}]: Not enough agents to start TAC. Registered agents: {}, minimum number of agents: {}."
                         .format(self.public_key, len(self.registered_agents), self.nb_agents))
            return False

    def on_message(self, msg_id: int, dialogue_id: int, origin: str, content: bytes):
        logger.debug("[ControllerAgent] on_message: msg_id={}, dialogue_id={}, origin={}"
                     .format(msg_id, dialogue_id, origin))
        response = self.handler.handle(content, origin)
        if response is not None:
            response_bytes = response.serialize()
            self.send_message(msg_id + 1, dialogue_id, origin, response_bytes)

    def register(self):
        """
        Register on the OEF as a TAC controller agent.
        :return: None.
        """
        desc = Description({"version": 1}, data_model=self.CONTROLLER_DATAMODEL)
        logger.debug("Registering with {} data model".format(desc.data_model.name))
        self.register_service(0, desc)

    def handle_register(self, request: Register) -> Optional[Response]:
        """
        Handle a register message.
        If the public key is already registered, answer with an error message.
        If this is the n_th registration request, where n is equal to nb_agents, then start the competition.

        :param request: the register request.
        :return: an Error response if an error occurred, else None.
        """
        public_key = request.public_key
        if public_key in self.registered_agents:
            error_msg = "Agent already registered: '{}'".format(public_key)
            logger.error(error_msg)
            return Error(error_msg)
        else:
            logger.debug("Agent registered: '{}'".format(public_key))
            self.registered_agents.add(public_key)
            return None

    def handle_unregister(self, request: Unregister) -> Optional[Response]:
        """
        Handle a unregister message.
        If the public key is not registered, answer with an error message.

        :param request: the register request.
        :return: an Error response if an error occurred, else None.
        """
        public_key = request.public_key
        if public_key not in self.registered_agents:
            error_msg = "Agent not registered: '{}'".format(public_key)
            logger.error(error_msg)
            return Error(error_msg)
        else:
            logger.debug("Agent unregistered: '{}'".format(public_key))
            self.registered_agents.remove(public_key)
            return None

    def handle_transaction(self, request: Transaction) -> Optional[Response]:
        """
        Handle a transaction request message.
        If the transaction is invalid (e.g. whether because )

        :param request: the transaction request.
        :return: an Error response if an error occurred, else None.
        """
        logger.debug("Handling transaction: {}".format(request))
        sender_id = self._agent_pbk_to_id[request.public_key]
        receiver_id = self._agent_pbk_to_id[request.counterparty]
        buyer_id, seller_id = (sender_id, receiver_id) if request.buyer else (receiver_id, sender_id)
        tx = GameTransaction(
            buyer_id,
            seller_id,
            request.amount,
            list(request.good_ids),
            list(request.quantities)
        )
        if self._current_game.is_transaction_valid(tx):
            return self._handle_valid_transaction(request, tx)
        else:
            return self._handle_invalid_transaction(request)

    def _start_competition(self):
        """Create a game and send the game setting to every registered agent."""
        # assert that there is no competition running.
        # TODO find a better way.
        assert self._current_game is None and self._agent_pbk_to_id is None
        self._create_game()
        self._send_game_data_to_agents()
        logger.debug("Started competition:\n{}".format(self._current_game.get_holdings_summary()))
        plantuml_gen.start_competition(self.public_key, self._current_game, self._agent_pbk_to_id)

    def _create_game(self) -> Game:
        """
        Create a TAC game.

        :return: a Game instance.
        """
        scores = list(reversed(range(self.nb_goods)))
        self._current_game = Game.generate_game(self.nb_agents, self.nb_goods, self.money_endowment, scores, self.fee)
        self._agent_pbk_to_id = dict(map(reversed, enumerate(self.registered_agents)))
        return self._current_game

    def _send_game_data_to_agents(self):
        """
        Send the data of every agent about the game (e.g. endowments, preferences, scores)

        :return: None.
        """
        for public_key in self._agent_pbk_to_id:
            agent_id = self._agent_pbk_to_id[public_key]
            game_data = self._current_game.get_game_data_by_agent_id(agent_id)
            game_data_response = GameData(
                game_data.balance,
                game_data.initial_endowment,
                game_data.preferences,
                game_data.scores,
                self.fee,
            )
            logger.debug("[{}]: sending GameData to '{}': {}"
                         .format(self.public_key, public_key, str(game_data_response)))
            self.send_message(0, 1, public_key, game_data_response.serialize())

    def _handle_valid_transaction(self, request: Transaction, tx: GameTransaction):
        """Handle a valid transaction."""
        self._current_game.settle_transaction(tx)
        tx_confirmation = TransactionConfirmation(request.transaction_id)
        self.send_message(0, 0, request.public_key, tx_confirmation.serialize())
        self.send_message(0, 0, request.counterparty, tx_confirmation.serialize())

        # log messages
        logger.debug("Transaction '{}' settled successfully.".format(request.transaction_id))
        logger.debug("Current state:\n{}".format(self._current_game.get_holdings_summary()))

        # plantuml entries
        plantuml_gen.handle_valid_transaction(self.public_key, request.public_key, request.counterparty, request.transaction_id, self._current_game)

        return None

    def _handle_invalid_transaction(self, request: Transaction):
        """Handle an invalid transaction."""
        plantuml_gen.handle_invalid_transaction(self.public_key, request.public_key, request.counterparty, request.transaction_id)
        return Error("Error in checking transaction.")

    def dump(self, directory: str = "data", experiment_name: Optional[str] = None) -> None:
        """
        Dump the details of the simulation.

        :param directory: the directory where experiments details are listed.
        :param experiment_name: the name of the folder where the data about experiment will be saved.
        :return: None.
        """
        experiment_name = experiment_name if experiment_name is not None else str(datetime.datetime.now())\
            .replace(" ", "_")
        experiment_dir = directory + "/" + experiment_name

        game_dict = {} if self._current_game is None else self._current_game.to_dict()

        os.makedirs(experiment_dir, exist_ok=True)
        with open(os.path.join(experiment_dir, "game.json"), "w") as f:
            json.dump(game_dict, f)


def main():
    args = parse_arguments()
    agent = ControllerAgent(public_key=args.public_key, oef_addr=args.oef_addr, oef_port=args.oef_port)

    agent.connect()
    agent.register()

    logger.debug("Running agent...")
    agent.run()


if __name__ == '__main__':
    main()


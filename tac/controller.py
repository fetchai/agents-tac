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
import logging
import pprint
from typing import Optional, Set, Dict

from oef.schema import DataModel, Description, AttributeSchema

from tac.core import TacAgent, Game, GameTransaction
from tac.helpers import PlantUMLGenerator
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
        """Dispatch the request to the right handler"""
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
                 fee: int = 1, version: int = 1, **kwargs):
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
        })))

        self.nb_agents = nb_agents
        self.money_endowment = money_endowment
        self.nb_goods = nb_goods
        self.fee = fee
        self.version = version

        self.registered_agents = set()  # type: Set[str]
        self.handler = ControllerHandler(self)

        self._current_game = None  # type: Optional[Game]
        self._agent_pbk_to_id = None  # type: Optional[Dict[str, int]]

    def register(self):
        desc = Description({"version": 1}, data_model=self.CONTROLLER_DATAMODEL)
        logger.debug("Registering with {} data model".format(desc.data_model.name))
        self.register_service(0, desc)

    def start_competition(self):
        """Create a game and send the game setting to every registered agent."""
        assert self._current_game is None and self._agent_pbk_to_id is None
        self._create_game()
        self._send_game_data_to_agents()
        logger.debug("Started competition:\n{}".format(self._current_game.get_holdings_summary()))

        agent_id_to_pbk = dict(map(reversed, self._agent_pbk_to_id.items()))
        for agent_id, game_state in enumerate(self._current_game.game_states):
            agent_pbk = agent_id_to_pbk[agent_id]
            self.add_drawable(PlantUMLGenerator.Note("{} game state: \n".format(agent_pbk) + str(game_state) +
                                                     "\nScore: {}".format(game_state.get_score()),
                                                     self.public_key))
            self.add_drawable(PlantUMLGenerator.Transition(self.public_key, agent_pbk,
                                                           "GameData(money, endowments, preferences, scores, fee)"))

    def _create_game(self) -> Game:
        instances_per_good = self.nb_agents
        scores = list(reversed(range(self.nb_goods)))
        self._current_game = Game.generate_game(self.nb_agents, self.nb_goods, self.money_endowment,
                                                instances_per_good, scores, self.fee)
        self._agent_pbk_to_id = dict(map(reversed, enumerate(self.registered_agents)))
        return self._current_game

    def _send_game_data_to_agents(self):
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

    def on_message(self, msg_id: int, dialogue_id: int, origin: str, content: bytes):
        logger.debug("[ControllerAgent] on_message: msg_id={}, dialogue_id={}, origin={}"
                     .format(msg_id, dialogue_id, origin))
        response = self.handler.handle(content, origin)
        if response is not None:
            response_bytes = response.serialize()
            self.send_message(msg_id + 1, dialogue_id, origin, response_bytes)

    def handle_register(self, request: Register) -> Optional[Response]:
        public_key = request.public_key
        if public_key in self.registered_agents:
            error_msg = "Agent already registered: '{}'".format(public_key)
            logger.error(error_msg)
            return Error(error_msg)
        else:
            logger.debug("Agent registered: '{}'".format(public_key))
            self.registered_agents.add(public_key)
            if len(self.registered_agents) >= self.nb_agents:
                self.start_competition()
            return None

    def handle_unregister(self, request: Unregister) -> Optional[Response]:
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
        logger.debug("Handling transaction: {}".format(request))
        sender_id = self._agent_pbk_to_id[request.public_key]
        receiver_id = self._agent_pbk_to_id[request.counterparty]
        buyer_id, seller_id = (sender_id, receiver_id) if request.buyer else (receiver_id, sender_id)
        tx = GameTransaction(
            buyer_id,
            seller_id,
            request.amount,
            request.good_ids,
            request.quantities
        )
        if self._current_game.is_transaction_valid(tx):
            self._current_game.settle_transaction(tx)
            tx_confirmation = TransactionConfirmation(request.transaction_id)
            self.send_message(0, 0, request.public_key, tx_confirmation.serialize())
            self.send_message(0, 0, request.counterparty, tx_confirmation.serialize())
            logger.debug("Transaction '{}' settled successfully.".format(request.transaction_id))
            logger.debug("Current state:\n{}".format(self._current_game.get_holdings_summary()))

            self.add_drawable(PlantUMLGenerator.Note("Transaction {} settled.".format(request.transaction_id),
                                                     self.public_key))
            self.add_drawable(PlantUMLGenerator.Note("New holdings:\n" + self._current_game.get_holdings_summary(),
                                                     self.public_key))
            self.add_drawable(PlantUMLGenerator.Note("Details:\n" + "\n"
                                                     .join(["score={}, money={}".format(g.get_score(), g.balance)
                                                            for g in self._current_game.game_states]),
                                                     self.public_key))

            self.add_drawable(PlantUMLGenerator.Transition(
                self.public_key, request.public_key, "ConfirmTransaction({})".format(request.transaction_id)))
            self.add_drawable(PlantUMLGenerator.Transition(
                self.public_key, request.counterparty, "ConfirmTransaction({})".format(request.transaction_id)))
            return None
        else:

            self.add_drawable(PlantUMLGenerator.Transition(
                self.public_key, request.public_key, "Error({})".format(request.transaction_id)))
            self.add_drawable(PlantUMLGenerator.Transition(
                self.public_key, request.counterparty, "Error({})".format(request.transaction_id)))
            return Error("Error in checking transaction.")


def main():
    args = parse_arguments()
    agent = ControllerAgent(public_key=args.public_key, oef_addr=args.oef_addr, oef_port=args.oef_port)

    agent.connect()
    agent.register()

    logger.debug("Running agent...")
    agent.run()


if __name__ == '__main__':
    main()


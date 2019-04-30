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

"""Baseline agent - version 2"""

import argparse
import asyncio
import datetime
import logging
import threading
from abc import abstractmethod
from typing import Optional, Callable, List, Dict, Any

from oef.dialogue import SingleDialogue, DialogueAgent
from oef.messages import CFP_TYPES, OEFErrorOperation, PROPOSE_TYPES
from oef.proxy import OEFNetworkProxy
from oef.query import Query, Constraint, GtEq
from oef.schema import DataModel

from tac.core import TACAgent
from tac.game import AgentState
from tac.helpers.misc import build_datamodel, TacError
from tac.protocol import GameData, Error, TransactionConfirmation, Response, Register

logger = logging.getLogger(__name__)


def parse_arguments():
    parser = argparse.ArgumentParser("baseline", description="Launch the baseline agent.")
    parser.add_argument("--public-key", default="baseline", help="Public key of the agent.")
    parser.add_argument("--oef-addr", default="127.0.0.1", help="TCP/IP address of the OEF Agent")
    parser.add_argument("--oef-port", default=3333, help="TCP/IP port of the OEF Agent")
    # parser.add_argument("--gui", action="store_true", help="Show the GUI.")

    return parser.parse_args()


class BaselineDialogue(SingleDialogue):

    def on_message(self, msg_id: int, content: bytes) -> None:
        pass

    def on_cfp(self, msg_id: int, target: int, query: CFP_TYPES) -> None:
        pass

    def on_propose(self, msg_id: int, target: int, proposal: PROPOSE_TYPES) -> None:
        pass

    def on_accept(self, msg_id: int, target: int) -> None:
        pass

    def on_decline(self, msg_id: int, target: int) -> None:
        pass

    def on_dialogue_error(self, answer_id: int, dialogue_id: int, origin: str) -> None:
        pass


class NegotiationAgent(DialogueAgent):

    def __init__(self, public_key: str, oef_addr: str, oef_port: int = 3333, **kwargs) -> None:
        super().__init__(OEFNetworkProxy(public_key, oef_addr, oef_port, **kwargs))
        self.controller = None  # type: Optional[str]
        self.agent_state = None  # type: Optional[AgentState]

        self.pending_search_ids = set()
        self.search_events = {} # type: Dict[int, asyncio.Event]
        self.search_results = {}  # type: Dict[int, List[str]]
        self.search_callbacks = {}  # type: Dict[int, Callable]

    def on_search_result(self, search_id: int, agents: List[str]):
        if search_id in self.pending_search_ids:
            # check if the search operation has a callback or it does not.
            if search_id in self.search_events:
                self.search_results[search_id] = agents
                self.search_events[search_id].set()
            elif search_id in self.search_callbacks:
                callback = self.search_callbacks[search_id]
                callback(self, agents)

    def search(self, query: Query, callback: Optional[Callable[['TACAgent', Any], Any]] = None) -> Optional[List[str]]:
        """
        Search for agents. It uses the SDK's search_services() method.
        The main purpose of this method is to implement a blocking call such that waits until the OEF answers with a list of agents.
        Or, specify a custom function callback that will be executed when the result arrives.

        :param query: the query for the search.
        :param callback: if None, the search operation is synchronous (that is, waits until the OEF answers with the result).
                         The callbacks accepts 'self' as first argument and a list of strings as second argument.
        :return: a list of agent's public keys. If a callback is provided, return None.
        """
        search_id = len(self.pending_search_ids)
        self.pending_search_ids.add(search_id)
        self.search_services(search_id, query)
        if callback is not None:
            # register a callback
            self.search_callbacks[search_id] = callback
            return None
        else:
            event = threading.Event()
            self.search_events[search_id] = event
            event.wait()
            result = self.search_results[search_id]
            self.pending_search_ids.remove(search_id)
            self.search_events.pop(search_id)
            self.search_results.pop(search_id)
            return result

    @abstractmethod
    def on_start(self, game_data: GameData) -> None:
        """
        On receiving game data from the TAC controller, do the setup.

        :param game_data: the set of parameters assigned to this agent by the TAC controller.
        :return: ``None``
        """

    @abstractmethod
    def on_transaction_confirmed(self, tx_confirmation: TransactionConfirmation) -> None:
        """
        Handle the transaction confirmation.

        :param tx_confirmation: the data of the confirmed transaction.
        :return: ``None``
        """

    @abstractmethod
    def on_tac_error(self, error: Error) -> None:
        """
        Handle error messages from the TAC controller.

        :return: ``None``
        """

    @abstractmethod
    def on_new_cfp(self, msg_id: int, dialogue_id: int, from_: str, target: int, query: CFP_TYPES) -> None:
        """
        Handle the arrival of a CFP message.

        :param msg_id: the message identifier for the dialogue.
        :param dialogue_id: the identifier of the dialogue in which the message is sent.
        :param from_: the identifier of the agent who sent the message.
        :param target: the identifier of the message to whom this message is answering.
        :param query: the query associated with the Call For Proposals.
        :return: ``None``
        """

    def on_new_message(self, msg_id: int, dialogue_id: int, from_: str, content: bytes) -> None:
        """TODO Temporarily assume we can receive simple messages only from the controller agent."""
        # here we can get a new message either from any agent, including the controller.
        # however, the one from the controller should be handled in a different way.
        # try to parse it as if it were a response from the Controller.

        response = None  # type: Optional[Response]
        try:
            response = Response.from_pb(content)
        except TacError as e:
            # the message was not a 'Response' message.
            logger.exception(str(e))

        if isinstance(response, GameData):
            self.on_start(response)
        elif isinstance(response, TransactionConfirmation):
            self.on_transaction_confirmed(response)
        elif isinstance(response, Error):
            self.on_tac_error(response)
        else:
            # TODO revise.
            raise TacError("No correct message received.")

    def register(self, tac_controller_pk: str) -> None:
        """Register to a competition.
        :param tac_controller_pk: the public key of the controller.
        :return: ``None``
        :raises AssertionError: if the agent is already registered.
        """
        assert self.controller is None and self.agent_state is None
        msg = Register(self.public_key).serialize()
        self.send_message(0, 0, tac_controller_pk, msg)

    def search_tac_controllers(self):
        pass


class BaselineAgentV2(NegotiationAgent):

    def __init__(self, public_key: str, oef_addr: str, oef_port: int = 3333, **kwargs) -> None:
        super().__init__(public_key, oef_addr, oef_port, **kwargs)

    @property
    def seller_data_model(self) -> DataModel:
        return build_datamodel(self.agent_state.nb_goods, seller=True)

    def on_start(self, game_data: GameData) -> None:

        # register as seller
        self._register_as_seller_for_excessing_goods()
        results = self.search(Query([Constraint("good_01", GtEq(0))], self.seller_data_model))
        print("On Start.", results)

    def on_transaction_confirmed(self, tx_confirmation: TransactionConfirmation) -> None:
        pass

    def on_tac_error(self, error: Error) -> None:
        pass

    def on_connection_error(self, operation: OEFErrorOperation) -> None:
        pass

    def on_new_cfp(self, msg_id: int, dialogue_id: int, from_: str, target: int, query: CFP_TYPES) -> None:
        pass

    def _register_as_seller_for_excessing_goods(self) -> None:
        # desc = get_baseline_seller_description(self.agent_state)
        # self.register_service(0, desc)
        pass


async def main():
    args = parse_arguments()
    start_time = datetime.datetime.now() + datetime.timedelta(0, 5)
    agent = BaselineAgentV2(public_key=args.public_key, oef_addr=args.oef_addr, oef_port=args.oef_port,
                            start_time=start_time)

    await agent.async_connect()
    agent_task = asyncio.ensure_future(agent.async_run())

    # result = await agent.search(Query([Constraint("version", GtEq(1))]), callback=lambda x, y: print(y))
    result = await agent.search(Query([Constraint("version", GtEq(1))]), callback=agent.on_start)
    print(result)

    logger.debug("Running agent...")
    await asyncio.sleep(3.0)


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())


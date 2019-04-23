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
import asyncio
import logging
from abc import abstractmethod
from typing import List, Dict, Optional, Callable

from oef.agents import OEFAgent, Agent
from oef.messages import CFP_TYPES, PROPOSE_TYPES
from oef.proxy import OEFNetworkProxy
from oef.query import Query, Constraint, GtEq
from oef.schema import Description

from tac.game import GameState
from tac.helpers.misc import TacError
from tac.helpers.plantuml import plantuml_gen
from tac.protocol import Register, Response, GameData, TransactionConfirmation, Error, Transaction

logger = logging.getLogger(__name__)


class TacAgent(OEFAgent):
    def __init__(self, public_key: str, oef_addr: str, oef_port: int = 3333, **kwargs) -> None:
        super().__init__(public_key, oef_addr, oef_port, **kwargs)

    def register_service(self, msg_id: int, service_description: Description) -> None:
        super().register_service(msg_id, service_description)
        plantuml_gen.register_service(self.public_key, service_description)

    def search_services(self, search_id: int, query: Query, additional_msg: str = "") -> None:
        super().search_services(search_id, query)
        plantuml_gen.search_services(self.public_key, query, additional_msg=additional_msg)

    def on_search_result(self, search_id: int, agents: List[str]):
        plantuml_gen.on_search_result(self.public_key, agents)

    def send_cfp(self, msg_id: int, dialogue_id: int, destination: str, target: int, query: CFP_TYPES) -> None:
        super().send_cfp(msg_id, dialogue_id, destination, target,query)
        plantuml_gen.send_cfp(self.public_key, destination, dialogue_id, "")

    def send_propose(self, msg_id: int, dialogue_id: int, destination: str, target: int,
                     proposals: PROPOSE_TYPES) -> None:
        super().send_propose(msg_id, dialogue_id, destination, target, proposals)
        plantuml_gen.send_propose(self.public_key, destination, dialogue_id, Description({}))


class NegotiationAgent(Agent):

    TAC_CONTROLLER_SEARCH_ID = 1

    def __init__(self, public_key: str, oef_addr: str, oef_port: int = 3333, **kwargs) -> None:
        super().__init__(OEFNetworkProxy(public_key, oef_addr, oef_port, **kwargs))

        # data about the current game
        self._controller = None  # type: Optional[str]
        self._game_state = None  # type: Optional[GameState]
        self._fee = None         # type: Optional[int]

        self._pending_transactions = {}  # type: Dict[str, Transaction]

    def reset(self):
        """
        Reset the agent to its initial condition.
        """
        self._controller = None
        self._game_state = None
        self._fee = None
        self._pending_transactions = {}

    def on_search_result(self, search_id: int, agents: List[str]):
        """Handle search results."""
        if search_id == self.TAC_CONTROLLER_SEARCH_ID:
            # assuming the number of active controller is only one.
            assert len(agents) == 1
            controller_public_key = agents[0]
            self.register(controller_public_key)
        else:
            self.on_search_results(search_id, agents)

    def on_search_results(self, search_id: int, agents: List[str]):
        """Handle search results. To be implemented by the developer.

        TODO this is different from the SDK's on_search_result,
             because that one is used for low-level operations."""

    @abstractmethod
    def on_start(self, game_data: GameData) -> None:
        """
        On receiving game data from the TAC controller, do the setup.

        :param game_data: the set of parameters assigned to this agent by the TAC controller.
        :return: ``None``
        """

    def _on_start(self, controller_public_key: str, game_data: GameData) -> None:
        """The private handler for the on_start event. It is used to populate
        data structures of the agent and remove the burden from the developer to do so."""

        # populate data structures about the started competition
        self._controller = controller_public_key
        self._game_state = GameState(game_data.money, game_data.endowment, game_data.preferences)
        self._fee = game_data.fee

        # dispatch the handling to the developer's implementation.
        self.on_start(game_data)

    @abstractmethod
    def on_transaction_confirmed(self, tx_confirmation: TransactionConfirmation) -> None:
        """
        Handle the transaction confirmation.

        :param tx_confirmation: the data of the confirmed transaction.
        :return: ``None``
        """
        transaction = self._pending_transactions.pop(tx_confirmation.transaction_id)
        self._game_state.update(transaction)

    @abstractmethod
    def on_tac_error(self, error: Error) -> None:
        """
        Handle error messages from the TAC controller.

        :return: ``None``
        """

    def on_message(self, msg_id: int, dialogue_id: int, origin: str, content: bytes) -> None:
        # here we can get a new message from any agent, including the controller.
        # however, the one from the controller should be handled in a different way.
        # try to parse it as if it were a response from the Controller Agent.

        response = None  # type: Optional[Response]
        try:
            response = Response.from_pb(content)
        except TacError as e:
            # the message was not a 'Response' message.
            logger.exception(str(e))

        if isinstance(response, GameData):
            controller_public_key = origin
            self._on_start(controller_public_key, response)
        elif isinstance(response, TransactionConfirmation):
            self.on_transaction_confirmed(response)
        elif isinstance(response, Error):
            self.on_tac_error(response)
        else:
            raise TacError("No correct message received.")

    def register_to_tac(self):
        """Search for active TAC Controller, and register to one of them.

        We assume that the controller is registered as a service with the 'tac' data model
        and with an attribute version = 1."""

        query = Query([Constraint("version", GtEq(1))])
        self.search_services(self.TAC_CONTROLLER_SEARCH_ID, query)
        # when the search result arrives, the on_search_result method is executed and
        # the actual registration request is sent.

    def register(self, tac_controller_pk: str) -> None:
        """Register to a competition.
        :param tac_controller_pk: the public key of the controller.
        :return: ``None``
        :raises AssertionError: if the agent is already registered.
        """
        assert self._controller is None and self._game_state is None
        msg = Register().serialize()
        self.send_message(0, 0, tac_controller_pk, msg)

    def submit_transaction(self, tx: Transaction):
        pass


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
import logging
from abc import abstractmethod
from typing import List, Optional

from oef.agents import OEFAgent
from oef.messages import CFP_TYPES, PROPOSE_TYPES, OEFErrorOperation
from oef.query import Query, Constraint, GtEq

from tac.game import AgentState, GameConfiguration, WorldState
from tac.helpers.misc import TacError
from tac.protocol import Register, Response, GameData, TransactionConfirmation, Error, Transaction, Cancelled

logger = logging.getLogger(__name__)


class NegotiationAgent(OEFAgent):
    """
    The negotiation agent is an agent class that is TAC compatible and defines a FIPA complient interface.
    """

    TAC_CONTROLLER_SEARCH_ID = 1

    def __init__(self, public_key: str, oef_addr: str, oef_port: int = 3333, is_world_modeling: bool = False, **kwargs) -> None:
        super().__init__(public_key, oef_addr, oef_port, **kwargs)

        self._controller_pbk = None  # type: Optional[str]
        self._game_configuration = None  # type: Optional[GameConfiguration]
        self._initial_agent_state = None  # type: Optional[AgentState]
        self._agent_state = None  # type: Optional[AgentState]
        self._is_world_modeling = is_world_modeling
        self._world_state = None  # type: Optional[WorldState]

    @property
    def controller_pbk(self):
        return self._controller_pbk

    @property
    def game_configuration(self):
        return self._game_configuration

    @property
    def initial_agent_state(self):
        return self._initial_agent_state

    @property
    def is_world_modeling(self):
        return self._is_world_modeling

    @abstractmethod
    def on_start(self) -> None:
        """
        On start of the competition, do the setup.

        :return: None
        """

    @abstractmethod
    def on_cancelled(self) -> None:
        """
        Handle the cancellation of the competition from the TAC controller.

        :return: None
        """

    @abstractmethod
    def on_search_results(self, search_id: int, agents: List[str]) -> None:
        """
        Handle search results.

        :return: None
        """
        # TODO this is different from the SDK's on_search_result, because that one is used for low-level operations.

    @abstractmethod
    def on_cfp(self, msg_id: int, dialogue_id: int, origin: str, target: int, query: CFP_TYPES) -> None:
        """
        Handle call for proposal message.

        :param msg_id: the message id
        :param dialogue_id: the dialogue id
        :param origin: the public key of the message sender.
        :param target: the targeted message id to which this message is a response.
        :param query: the query associated with the cfp.

        :return: None
        """

    @abstractmethod
    def on_propose(self, msg_id: int, dialogue_id: int, origin: str, target: int, proposals: PROPOSE_TYPES) -> None:
        """
        On propose dispatcher.

        :param msg_id: the message id
        :param dialogue_id: the dialogue id
        :param origin: the public key of the message sender.
        :param target: the targeted message id to which this message is a response.
        :param proposals: the proposals associated with the message.

        :return: None
        """

    @abstractmethod
    def on_decline(self, msg_id: int, dialogue_id: int, origin: str, target: int) -> None:
        """
        On Decline handler.

        :param msg_id: the message id
        :param dialogue_id: the dialogue id
        :param origin: the public key of the message sender.
        :param target: the targeted message id to which this message is a response.

        :return: None
        """

    @abstractmethod
    def on_accept(self, msg_id: int, dialogue_id: int, origin: str, target: int) -> None:
        """
        On Accept handler.

        :param msg_id: the message id
        :param dialogue_id: the dialogue id
        :param origin: the public key of the message sender.
        :param target: the targeted message id to which this message is a response.

        :return: None
        """

    @abstractmethod
    def on_transaction_confirmed(self, tx_confirmation: TransactionConfirmation) -> None:
        """
        On Transaction confirmed handler.

        :param tx_confirmation: the transaction confirmation

        :return: None
        """

    @abstractmethod
    def on_tac_error(self, error: Error) -> None:
        """
        Handle error messages from the TAC controller.

        :return: None
        """

    ###
    # The following methods do not need to be implemented by the developer.
    ###

    def on_oef_error(self, answer_id: int, operation: OEFErrorOperation):
        logger.debug("Receiver OEF error: answer_id={}, operation={}".format(answer_id, operation))

    def on_message(self, msg_id: int, dialogue_id: int, origin: str, content: bytes) -> None:
        """
        Handle any message from the OEF not handled by specific handlers.

        :param msg_id: the message id
        :param dialogue_id: the dialogue id
        :param origin: the public key of the message sender.
        :param content: the message content.

        :return: None
        """
        # here we can get a new message from any agent, including the controller.
        # however, the one from the controller should be handled in a different way.
        # try to parse it as if it were a response from the Controller Agent.
        # TODO this should really be called: on_other_message

        response = None  # type: Optional[Response]
        try:
            response = Response.from_pb(content, origin)
        except TacError as e:
            # the message was not a 'Response' message.
            logger.exception(str(e))

        if isinstance(response, GameData):
            controller_public_key = origin
            self._on_start(controller_public_key, response)
        elif isinstance(response, TransactionConfirmation):
            self.on_transaction_confirmed(response)
        elif isinstance(response, Cancelled):
            self.on_cancelled()
        elif isinstance(response, Error):
            self.on_tac_error(response)
        else:
            raise TacError("No correct message received.")

    def _on_start(self, controller_public_key: str, game_data: GameData) -> None:
        """
        The private handler for the on_start event. It is used to populate
        data structures of the agent and remove the burden from the developer to do so.

        :param controller_public_key: the public key of the controller
        :param game_data: the data sent from the controller about the game.

        :return: None
        """

        # populate data structures about the started competition
        self._controller_pbk = controller_public_key
        self._game_configuration = GameConfiguration(game_data.nb_agents, game_data.nb_goods, game_data.tx_fee, game_data.agent_pbks, game_data.good_pbks)
        self._initial_agent_state = AgentState(game_data.money, game_data.endowment, game_data.utility_params)
        self._agent_state = AgentState(game_data.money, game_data.endowment, game_data.utility_params)
        if self.is_world_modeling:
            opponent_pbks = self.game_configuration.agent_pbks
            opponent_pbks.remove(self.public_key)
            self._world_state = WorldState(opponent_pbks, self.game_configuration.good_pbks, self.initial_agent_state)

        # dispatch the handling to the developer's implementation.
        self.on_start()

    def on_search_result(self, search_id: int, agent_pbks: List[str]) -> None:
        """
        Handle search results.

        :param search_id: the id set in the search query
        :param agent_pbks: a list of agent pbks

        :return: None
        """
        agent_pbks = list(set(agent_pbks))
        if search_id == self.TAC_CONTROLLER_SEARCH_ID:
            # assuming the number of active controller is only one.
            assert len(agent_pbks) == 1
            controller_public_key = agent_pbks[0]
            self.register_to_tac(controller_public_key)
        else:
            self.on_search_results(search_id, agent_pbks)

    def search_for_tac(self) -> None:
        """
        Search for active TAC Controller.

        We assume that the controller is registered as a service with the 'tac' data model
        and with an attribute version = 1.

        :return: None
        """
        query = Query([Constraint("version", GtEq(1))])
        self.search_services(self.TAC_CONTROLLER_SEARCH_ID, query)

    def register_to_tac(self, tac_controller_pk: str) -> None:
        """
        Register to active TAC Controller.

        :param tac_controller_pk: the public key of the controller.

        :return: None
        :raises AssertionError: if the agent is already registered.
        """
        assert self.controller_pbk is None and self.game_configuration is None and self._agent_state is None
        msg = Register(self.public_key).serialize()
        self.send_message(0, 0, tac_controller_pk, msg)

    def submit_transaction_to_controller(self, tx: Transaction) -> None:
        """
        Submit a transaction request to the controller

        :param tx: the transaction request.

        :return: None
        """
        dialogue_id = abs(hash(tx.transaction_id) % 2**31)
        self.send_message(0, dialogue_id, self._controller_pbk, tx.serialize())

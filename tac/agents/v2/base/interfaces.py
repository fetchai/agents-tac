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
from abc import abstractmethod
from typing import Union

from oef.messages import CFP, Propose, Accept, Decline, Message as SimpleMessage, SearchResult, OEFErrorMessage, DialogueErrorMessage

from tac.platform.protocol import Error, TransactionConfirmation, StateUpdate, GameData

AgentMessage = Union[SimpleMessage, CFP, Propose, Accept, Decline]


class ControllerReactionInterface:
    """
    This interface contains the methods to react to events from the ControllerAgent.
    """

    @abstractmethod
    def on_dialogue_error(self, dialogue_error_msg: DialogueErrorMessage) -> None:
        """
        Handles dialogue error event emitted by the controller.

        :param dialogue_error_msg: the dialogue error message
        :return: None
        """

    @abstractmethod
    def on_start(self, game_data: GameData) -> None:
        """
        On start of the competition, do the setup.

        :param game_data: the data for the started game.
        :return: None
        """

    @abstractmethod
    def on_cancelled(self) -> None:
        """
        Handle the cancellation of the competition from the TAC controller.

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
    def on_state_update(self, agent_state: StateUpdate) -> None:
        """
        On receiving the agent state update.

        :param agent_state: the current state of the agent in the competition.

        :return: None
        """

    @abstractmethod
    def on_tac_error(self, error: Error) -> None:
        """
        Handle error messages from the TAC controller.

        :return: None
        """


class ControllerActionInterface:
    """
    This interface contains the methods to interact with the ControllerAgent.
    """

    @abstractmethod
    def request_state_update(self) -> None:
        """
        Request a state update from the controller.

        :return: None
        """


class OEFSearchReactionInterface:
    """
    This interface contains the methods to react to events from the OEF.
    """

    @abstractmethod
    def on_search_result(self, search_result: SearchResult) -> None:
        """
        Handle search results.

        :param search_result: the search result
        :return: None
        """

    @abstractmethod
    def on_oef_error(self, oef_error: OEFErrorMessage) -> None:
        """
        Handle an OEF error message.

        :param oef_error: the oef error
        :return: None
        """

    @abstractmethod
    def on_dialogue_error(self, dialogue_error: DialogueErrorMessage) -> None:
        """
        Handler a dialogue error message

        :param dialogue_error_msg: the dialogue error message
        :return: None
        """


class OEFSearchActionInterface:
    """
    This interface contains the methods to interact with the OEF.
    """

    @abstractmethod
    def search_for_tac(self) -> None:
        """
        Search for active TAC Controller.

        :return: None
        """

    @abstractmethod
    def update_services(self) -> None:
        """
        Update services on OEF Service Directory

        :return: None
        """

    @abstractmethod
    def unregister_service(self) -> None:
        """
        Unregister service from OEF Service Directory.

        :return: None
        """

    @abstractmethod
    def register_service(self) -> None:
        """
        Register services to OEF Service Directory.

        :return: None
        """

    @abstractmethod
    def search_services(self) -> None:
        """
        Search services on OEF Service Directory.

        :return: None
        """


class DialogueReactionInterface:
    """
    This interface contains the methods to react to events from other agents.
    """

    @abstractmethod
    def on_new_dialogue(self, msg: AgentMessage) -> None:
        """Given a new message, create a Dialogue object that specifies:
        - the protocol rules that messages must follow;
        - how the agent behaves in this dialogue.

        :param msg: the agent message
        :return: None
        """

    @abstractmethod
    def on_existing_dialogue(self, msg: AgentMessage) -> None:
        """
        React to a message of an existing dialogue.

        :param msg: the agent message
        :return: None
        """

    @abstractmethod
    def on_unidentified_dialogue(self, msg: AgentMessage) -> None:
        """
        React to a message of an unidentified dialogue.

        :param msg: the agent message
        :return: None
        """


class DialogueActionInterface:
    """
    This interface contains the methods to interact with other agents.
    """

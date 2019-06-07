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

from oef.messages import Message as SearchResult, OEFErrorMessage, DialogueErrorMessage

from tac.experimental.core.tac.dialogues import Dialogue
from tac.protocol import Error, TransactionConfirmation, StateUpdate


class ControllerInterface:
    """
    This interface contains the methods to interact with the ControllerAgent.
    """

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


class OEFSearchInterface:
    """
    This interface contains the methods to maintain OEF search logic.
    """

    @abstractmethod
    def on_search_result(self, search_result: SearchResult):
        """Handle search results."""

    @abstractmethod
    def on_oef_error(self, oef_error: OEFErrorMessage):
        """Handle an OEF error message."""

    @abstractmethod
    def on_dialogue_error(self, dialogue_error: DialogueErrorMessage):
        """Handler a dialogue error message"""


class DialogueInterface:
    """
    This interface contains the methods to maintain a Dialogue with other agents.
    """

    @abstractmethod
    def on_new_dialogue(self, msg) -> Dialogue:
        """Given a new message, create a Dialogue object that specifies:
        - the protocol rules that messages must follow;
        - how the agent behaves in this dialogue.
        """

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

"""This module defines the interfaces which a TAC compatible agent must implement."""

from abc import abstractmethod

from aea.mail.base import Envelope, Address
from aea.protocols.base.message import Message


class ControllerReactionInterface:
    """This interface contains the methods to react to events from the ControllerAgent."""

    @abstractmethod
    def on_dialogue_error(self, envelope: Envelope, sender: Address) -> None:
        """
        Handle dialogue error event emitted by the controller.

        :param envelope: the dialogue error message
        :param sender: the address of the sender

        :return: None
        """

    @abstractmethod
    def on_start(self, message: Message, sender: Address) -> None:
        """
        On start of the competition, do the setup.

        :param message: the message
        :param sender: the address of the sender

        :return: None
        """

    @abstractmethod
    def on_cancelled(self) -> None:
        """
        Handle the cancellation of the competition from the TAC controller.

        :return: None
        """

    @abstractmethod
    def on_transaction_confirmed(self, message: Message, sender: Address) -> None:
        """
        On Transaction confirmed handler.

        :param message: the message
        :param sender: the address of the sender

        :return: None
        """

    @abstractmethod
    def on_state_update(self, message: Message, sender: Address) -> None:
        """
        On receiving the agent state update.

        :param message: the message
        :param sender: the address of the sender

        :return: None
        """

    @abstractmethod
    def on_tac_error(self, message: Message, sender: Address) -> None:
        """
        Handle error messages from the TAC controller.

        :param message: the message
        :param sender: the address of the sender

        :return: None
        """


class ControllerActionInterface:
    """This interface contains the methods to interact with the ControllerAgent."""

    @abstractmethod
    def request_state_update(self) -> None:
        """
        Request a state update from the controller.

        :return: None
        """


class OEFReactionInterface:
    """This interface contains the methods to react to events from the OEF."""

    @abstractmethod
    def on_search_result(self, search_result: Message) -> None:
        """
        Handle search results.

        :param search_result: the search result

        :return: None
        """

    @abstractmethod
    def on_oef_error(self, oef_error: Message) -> None:
        """
        Handle an OEF error message.

        :param oef_error: the oef error

        :return: None
        """

    @abstractmethod
    def on_dialogue_error(self, dialogue_error: Message) -> None:
        """
        Handle a dialogue error message.

        :param dialogue_error_msg: the dialogue error message

        :return: None
        """


class OEFActionInterface:
    """This interface contains the methods to interact with the OEF."""

    @abstractmethod
    def search_for_tac(self) -> None:
        """
        Search for active TAC Controller.

        :return: None
        """

    @abstractmethod
    def update_services(self) -> None:
        """
        Update services on OEF Service Directory.

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
    """This interface contains the methods to react to events from other agents."""

    @abstractmethod
    def on_new_dialogue(self, message: Message, sender: Address) -> None:
        """
        React to a message for a new dialogue.

        Given a new message, create a Dialogue object that specifies:
        - the protocol rules that messages must follow;
        - how the agent behaves in this dialogue.

        :param message: the agent message
        :param sender: the address of the sender

        :return: None
        """

    @abstractmethod
    def on_existing_dialogue(self, message: Message, sender: Address) -> None:
        """
        React to a message of an existing dialogue.

        :param message: the agent message
        :param sender: the address of the sender

        :return: None
        """

    @abstractmethod
    def on_unidentified_dialogue(self, message: Message, sender: Address) -> None:
        """
        React to a message of an unidentified dialogue.

        :param message: the agent message
        :param sender: the address of the sender

        :return: None
        """


class DialogueActionInterface:
    """This interface contains the methods to interact with other agents."""

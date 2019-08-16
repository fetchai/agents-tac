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

"""
This module defines the interfaces which a TAC compatible agent must implement.

It cointains:
- OEFReactionInterface: This interface contains the methods to react to events from the OEF.
- OEFActionInterface: This interface contains the methods to interact with the OEF.
"""

from abc import abstractmethod

from oef.messages import Message as OEFErrorMessage, DialogueErrorMessage


class OEFReactionInterface:
    """This interface contains the methods to react to events from the OEF."""

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
        Handle a dialogue error message.

        :param dialogue_error_msg: the dialogue error message

        :return: None
        """


class OEFActionInterface:
    """This interface contains the methods to interact with the OEF."""

    @abstractmethod
    def register_service(self) -> None:
        """
        Register services to OEF Service Directory.

        :return: None
        """

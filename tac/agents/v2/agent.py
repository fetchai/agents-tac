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
from typing import Optional

from tac.agents.v2.mail import MailBox, InBox, OutBox
from tac.helpers.crypto import Crypto

logger = logging.getLogger(__name__)


class Liveness:
    """
    Determines the liveness of the agent.
    """
    def __init__(self):
        self._is_stopped = True

    @property
    def is_stopped(self):
        return self._is_stopped


class Agent:
    def __init__(self, name: str, oef_addr: str, oef_port: int = 3333):
        self._name = name
        self._crypto = Crypto()
        self._liveness = Liveness()

        self.mail_box = None  # type: Optional[MailBox]
        self.in_box = None  # type: Optional[InBox]
        self.out_box = None  # type: Optional[OutBox]

    @property
    def name(self) -> str:
        return self._name

    @property
    def crypto(self) -> Crypto:
        return self._crypto

    @property
    def liveness(self):
        return self._liveness

    def start(self) -> None:
        """
        Starts the mailbox.

        :return: None
        """
        self.mail_box.start()
        self.liveness._is_stopped = False
        self.run_main_loop()

    def run_main_loop(self) -> None:
        """
        Runs the main loop of the agent
        """
        logger.debug("[{}]: Start processing messages...".format(self.name))
        while not self.liveness.is_stopped:
            self.act()
            self.react()

        self.stop()
        logger.debug("[{}]: Exiting main loop...".format(self.name))

    def stop(self) -> None:
        """
        Stops the mailbox.

        :return: None
        """
        logger.debug("[{}]: Stopping message processing...".format(self.name))
        self.liveness._is_stopped = True
        self.mail_box.stop()

    @abstractmethod
    def act(self) -> None:
        """
        Performs actions.

        :return: None
        """

    @abstractmethod
    def react(self) -> None:
        """
        Reacts to incoming events.

        :return: None
        """

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

"""Test miscellaneous features for the agent module."""
import time
from threading import Thread

import pytest

from tac.agents.v1.agent import Agent

from tac.agents.v1.base.participant_agent import ParticipantAgent
from tac.agents.v1.examples.strategy import BaselineStrategy
from tac.agents.v1.mail import FIPAMailBox


class TestAgent(Agent):
    """A class to implement an agent for testing."""

    def __init__(self, **kwargs):
        """Initialize the test agent."""
        super().__init__("test_agent", "127.0.0.1", 10000, **kwargs)
        self.mail_box = FIPAMailBox(self.crypto.public_key, "127.0.0.1", 10000)

    def act(self) -> None:
        """Perform actions."""

    def react(self) -> None:
        """React to incoming events."""

    def update(self) -> None:
        """Update the current state of the agent."""


def test_debug_flag_true():
    """
    Test that the debug mode works correctly.

    That is, an agent can be initialized without the OEF running.
    """
    test_agent = TestAgent(debug=True)
    job = Thread(target=test_agent.start)
    job.start()
    time.sleep(1.0)
    test_agent.stop()
    job.join()

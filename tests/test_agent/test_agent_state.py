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

"""Test the agent state."""

import time
from threading import Thread

from aea.agent import Agent, AgentState
from aea.channels.oef.connection import OEFMailBox


class TAgent(Agent):
    """A class to implement an agent for testing."""

    def __init__(self):
        """Initialize the test agent."""
        super().__init__("test_agent")
        self.mailbox = OEFMailBox(self.crypto.public_key, "127.0.0.1", 10000)

    def setup(self) -> None:
        """Set up the agent."""
        pass

    def teardown(self) -> None:
        """Teardown."""
        pass

    def act(self) -> None:
        """Perform actions."""

    def react(self) -> None:
        """React to incoming events."""

    def update(self) -> None:
        """Update the current state of the agent."""


def test_agent_initiated():
    """Test that when the agent is initiated, her state is AgentState.INITIATED."""
    test_agent = TAgent()
    assert test_agent.agent_state == AgentState.INITIATED


def test_agent_connected(network_node):
    """Test that when the agent is connected, her state is AgentState.CONNECTED."""
    test_agent = TAgent()
    test_agent.mailbox.connect()
    assert test_agent.agent_state == AgentState.CONNECTED
    test_agent.mailbox.disconnect()


def test_agent_running(network_node):
    """Test that when the agent is running, her state is AgentState.RUNNING."""
    test_agent = TAgent()
    job = Thread(target=test_agent.start)
    job.start()
    time.sleep(1.0)
    assert test_agent.agent_state == AgentState.RUNNING
    test_agent.stop()
    job.join()

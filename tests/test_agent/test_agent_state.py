# -*- coding: utf-8 -*-
import time
from threading import Thread

from tac.agents.v1.agent import Agent, AgentState
from tac.agents.v1.mail import FIPAMailBox


class TestAgent(Agent):
    """A class to implement an agent for testing."""

    def __init__(self):
        super().__init__("test_agent", "127.0.0.1", 10000)
        self.mail_box = FIPAMailBox(self.crypto.public_key, "127.0.0.1", 10000)

    def act(self) -> None:
        """Perform actions."""

    def react(self) -> None:
        """React to incoming events."""

    def update(self) -> None:
        """Update the current state of the agent."""


def test_agent_initiated():
    """Test that when the agent is initiated, her state is AgentState.INITIATED"""
    test_agent = Agent("test_agent", "127.0.0.1", 10000)
    assert test_agent.agent_state == AgentState.INITIATED


def test_agent_connected(network_node):
    """Test that when the agent is connected, her state is AgentState.CONNECTED"""
    test_agent = TestAgent()
    assert test_agent.agent_state == AgentState.CONNECTED
    test_agent.stop()


def test_agent_running(network_node):
    """Test that when the agent is running, her state is AgentState.RUNNING"""
    test_agent = TestAgent()
    job = Thread(target=test_agent.start)
    job.start()
    time.sleep(1.0)
    assert test_agent.agent_state == AgentState.RUNNING
    test_agent.stop()
    job.join()


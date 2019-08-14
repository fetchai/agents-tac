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
from threading import Timer
from unittest.mock import patch, MagicMock

from tac.agents.v1.agent import Agent
from tac.agents.v1.mail import FIPAMailBox, InBox, OutBox, OutContainer


class TestAgent(Agent):
    """A class to implement an agent for testing."""

    def __init__(self, **kwargs):
        """Initialize the test agent."""
        super().__init__("test_agent", "127.0.0.1", 10000, **kwargs)
        self.mail_box = FIPAMailBox(self.crypto.public_key, "127.0.0.1", 10000, debug=kwargs.get("debug", False))
        self.in_box = InBox(self.mail_box)
        self.out_box = OutBox(self.mail_box)

    def act(self) -> None:
        """Perform actions."""

    def react(self) -> None:
        """React to incoming events."""

    def update(self) -> None:
        """Update the current state of the agent."""


def test_that_when_debug_flag_true_we_can_run_main_loop_without_oef():
    """
    Test that, in debug mode, the agent's main loop can be run without the OEF running.

    In particular, assert that the methods 'act', 'react' and 'update' are called.
    """
    test_agent = TestAgent(debug=True)

    test_agent.act = MagicMock(test_agent.act)
    test_agent.react = MagicMock(test_agent.react)
    test_agent.update = MagicMock(test_agent.update)

    job = Timer(1.0, test_agent.stop)
    job.start()
    test_agent.start()
    job.join()

    test_agent.act.assert_called()
    test_agent.react.assert_called()
    test_agent.update.assert_called()


def test_that_when_debug_flag_true_we_drop_out_messages():
    """Test that, in debug mode, the out messages are dropped and a warning message is logged."""
    with patch('logging.Logger.warning') as mock:
        test_agent = TestAgent(debug=True)
        job = Timer(1.0, test_agent.stop)
        job.start()
        msg = OutContainer(b"this is a message.", 0, 0, "destination")
        test_agent.out_box.out_queue.put_nowait(msg)
        test_agent.out_box.send_nowait()
        test_agent.start()
        job.join()

        mock.assert_called_with("Dropping message of type '<class 'bytes'>' from the out queue...")

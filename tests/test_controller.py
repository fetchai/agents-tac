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

"""This module contains the tests of the controller module."""

import datetime
import logging
from threading import Thread

import pytest
from aea.crypto.base import Crypto
from aea.protocols.tac.message import TACMessage
from aea.protocols.tac.serialization import TACSerializer

from tac.agents.controller.agent import ControllerAgent
from tac.agents.controller.base.tac_parameters import TACParameters
from tac.gui.monitor import NullMonitor
from .common import TOEFAgent


logger = logging.getLogger(__name__)


class TestCompetitionStopsNoAgentRegistered:
    """Test the case when the controller starts, and no agent registers."""

    @pytest.fixture(autouse=True)
    def _start_oef_node(self, network_node):
        pass

    @classmethod
    def setup_class(cls):
        """Test that if the controller agent does not receive enough registrations, it stops."""
        tac_parameters = TACParameters(min_nb_agents=2, start_time=datetime.datetime.now(), registration_timeout=5)
        cls.controller_agent = ControllerAgent('controller', '127.0.0.1', 10000, tac_parameters, NullMonitor())

    def test_no_registered_agents(self):
        """Test no agent is registered."""
        job = Thread(target=self.controller_agent.start)
        job.start()
        job.join(20.0)
        assert not job.is_alive()
        assert len(self.controller_agent.game_handler.registered_agents) == 0

    @classmethod
    def teardown_class(cls):
        """Teardown test class."""
        cls.controller_agent.stop()


class TestCompetitionStopsTooFewAgentRegistered:
    """Test the case when the controller starts, and not enough agents register for TAC."""

    @pytest.fixture(autouse=True)
    def _start_oef_node(self, network_node):
        pass

    @classmethod
    def setup_class(cls):
        """Test that if the controller agent does not receive enough registrations, it stops."""
        tac_parameters = TACParameters(min_nb_agents=2, start_time=datetime.datetime.now(), registration_timeout=5)
        cls.controller_agent = ControllerAgent('controller', '127.0.0.1', 10000, tac_parameters, NullMonitor())

        cls.controller_agent.mailbox.connect()
        job = Thread(target=cls.controller_agent.start)
        job.start()

        cls.crypto = Crypto()
        cls.agent1 = TOEFAgent(cls.crypto.public_key, oef_addr='127.0.0.1', oef_port=10000)
        cls.agent1.connect()

        tac_msg = TACMessage(tac_type=TACMessage.Type.REGISTER, agent_name='agent_name')
        tac_bytes = TACSerializer().encode(tac_msg)
        cls.agent1.outbox.put_message(to=cls.controller_agent.crypto.public_key, sender=cls.crypto.public_key, protocol_id=TACMessage.protocol_id, message=tac_bytes)

        job.join()

    def test_only_one_agent_registered(self):
        """Test exactly one agent is registered."""
        assert len(self.controller_agent.game_handler.registered_agents) == 1
        agent_pbk = next(iter(self.controller_agent.game_handler.registered_agents))
        assert agent_pbk == self.crypto.public_key

    def test_agent_receives_cancelled_message(self):
        """Test the agent receives a cancelled message."""
        counter = 0
        while not self.agent1.inbox.empty():
            counter += 1
            msg = self.agent1.inbox.get_nowait()
            assert msg is not None and msg.sender == self.controller_agent.crypto.public_key
        assert counter == 1

    @classmethod
    def teardown_class(cls):
        """Teardown test class."""
        cls.controller_agent.stop()
        cls.agent1.disconnect()

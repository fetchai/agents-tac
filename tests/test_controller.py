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
# import multiprocessing
import pytest
import time
from threading import Thread

from aea.protocols.tac.message import TACMessage
from aea.protocols.tac.serialization import TACSerializer
from .common import TOEFAgent

from aea.crypto.base import Crypto
from tac.agents.controller.agent import ControllerAgent
from tac.agents.controller.base.tac_parameters import TACParameters

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
        cls.controller_agent = ControllerAgent('controller', '127.0.0.1', 10000, tac_parameters)

    def test_no_registered_agents(self):
        """Test no agent is registered."""
        job = Thread(target=self.controller_agent.start)
        job.start()
        job.join(10.0)
        assert not job.is_alive()
        assert len(self.controller_agent.game_handler.registered_agents) == 0
        self.controller_agent.stop()


class TestCompetitionStopsTooFewAgentRegistered:
    """Test the case when the controller starts, and not enough agents register for TAC."""

    @pytest.fixture(autouse=True)
    def _start_oef_node(self, network_node):
        pass

    @classmethod
    def setup_class(cls):
        """Test that if the controller agent does not receive enough registrations, it stops."""
        tac_parameters = TACParameters(min_nb_agents=2, start_time=datetime.datetime.now(), registration_timeout=5)
        cls.controller_agent = ControllerAgent('controller', '127.0.0.1', 10000, tac_parameters)

        crypto = Crypto()
        cls.agent1 = TOEFAgent(crypto.public_key, oef_addr='127.0.0.1', oef_port=10000)
        cls.agent1.connect()

        job = Thread(target=cls.controller_agent.start)
        job.start()
        agent_job = Thread(target=cls.agent1.run)
        agent_job.start()

        tac_msg = TACMessage(type=TACMessage.Type.REGISTER, agent_name='agent_name')
        tac_bytes = TACSerializer().encode(tac_msg)
        cls.agent1.outbox.put_message(to=cls.controller_agent.crypto.public_key, sender=crypto.public_key, protocol_id=TACMessage.protocol_id, message=tac_bytes)

        time.sleep(10.0)

        job.join()
        cls.agent1.stop()
        agent_job.join()

    def test_only_one_agent_registered(self):
        """Test exactly one agent is registered."""
        assert len(self.controller_agent.game_handler.registered_agents) == 1

    def test_agent_receives_cancelled_message(self):
        """Test the agent receives a cancelled message."""
        counter = 0
        while not self.agent1.inbox.empty():
            counter += 1
            msg = self.inbox.get_nowait()
            assert msg is not None
        assert counter == 1

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

from oef.agents import OEFAgent
# from oef.core import AsyncioCore  # OEF-SDK 0.6.1

from tac.helpers.crypto import Crypto
from tac.platform.controller.controller_agent import ControllerAgent
from tac.platform.controller.tac_parameters import TACParameters
from tac.platform.protocol import Register

logger = logging.getLogger(__name__)


class TestController:
    """Class to test the controller."""

    def test_competition_stops_too_few_registered_agents(self, network_node):
        """Test that if the controller agent does not receive enough registrations, it stops."""
        controller_agent = ControllerAgent(version=1)
        controller_agent.connect()

        parameters = TACParameters(min_nb_agents=2, start_time=datetime.datetime.now(), registration_timeout=5)
        job = Thread(target=controller_agent.handle_competition, args=(parameters,))
        job.start()

        crypto = Crypto()

        # core = AsyncioCore(logger=logger)  # OEF-SDK 0.6.1
        # core.run_threaded()  # OEF-SDK 0.6.1
        import asyncio
        agent1 = OEFAgent(crypto.public_key, oef_addr='127.0.0.1', oef_port=10000, loop=asyncio.new_event_loop())
        # agent1 = OEFAgent(crypto.public_key, oef_addr='127.0.0.1', oef_port=10000, core=core)  # OEF-SDK 0.6.1
        agent1.connect()
        agent1.send_message(0, 0, controller_agent.public_key, Register(agent1.public_key, crypto, 'agent_name').serialize())

        job.join()

        assert len(controller_agent.game_handler.registered_agents) == 1

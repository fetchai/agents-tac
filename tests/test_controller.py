# -*- coding: utf-8 -*-
import asyncio
import datetime
from threading import Thread

import pytest
from oef.agents import OEFAgent
from tac.platform.protocol import Register

from tac.platform.controller import ControllerAgent, TACParameters
from tac.helpers.crypto import Crypto


class TestController:

    def test_competition_stops_too_few_registered_agents(self, network_node):
        """
        Test that if the controller agent does not receive enough registrations, it stops.
        """

        controller_agent = ControllerAgent()
        controller_agent.connect()

        parameters = TACParameters(min_nb_agents=2, start_time=datetime.datetime.now(), registration_timeout=15)
        job = Thread(target=controller_agent.start_competition, args=(parameters, ))
        job.start()

        crypto = Crypto()
        agent1 = OEFAgent(crypto.public_key, "127.0.0.1", 10000, loop=asyncio.new_event_loop())
        agent1.connect()
        agent1.send_message(0, 0, controller_agent.public_key, Register(agent1.public_key, crypto, 'agent_name').serialize())

        job.join()

        assert len(controller_agent.game_handler.registered_agents) == 1

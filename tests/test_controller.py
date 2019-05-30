# -*- coding: utf-8 -*-
import asyncio
import datetime
from threading import Thread

from oef.agents import OEFAgent
from tac.protocol import Register

from tac.agents.controller import ControllerAgent, TACParameters


class TestController:
    
    def test_competition_stops_too_few_registered_agents(self, network_node):
        """
        Test that if the controller agent does not receive enough registrations, it stops.
        """

        controller_agent = ControllerAgent("controller")
        controller_agent.connect()

        parameters = TACParameters(min_nb_agents=2, start_time=datetime.datetime.now(), inactivity_timeout=10)
        job = Thread(target=controller_agent.start_competition, args=(parameters, ))
        job.start()

        agent1 = OEFAgent("agent1", "127.0.0.1", 3333, loop=asyncio.new_event_loop())
        agent1.connect()
        agent1.send_message(0, 0, 'controller', Register(agent1.public_key).serialize())

        job.join()

        assert len(controller_agent.game_handler.registered_agents) == 1


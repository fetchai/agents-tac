# -*- coding: utf-8 -*-
import time

from tac.agents.controller import ControllerAgent


class TestController:
    
    def test_controller(self, network_node):
        controller_agent = ControllerAgent()
        controller_agent.connect()

        time.sleep(1.0)
        controller_agent.disconnect()

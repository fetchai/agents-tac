#!/usr/bin/env python3
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

import argparse
import json
import logging
from typing import Optional, Set

from oef.schema import DataModel, Description

from tac.core import TacAgent
from tac.protocol import Request, Methods

logger = logging.getLogger(__name__)


def parse_arguments():
    parser = argparse.ArgumentParser("controller", description="Launch the controller agent.")
    parser.add_argument("--public-key", default="controller", help="Public key of the agent.")
    parser.add_argument("--oef-addr", default="127.0.0.1", help="TCP/IP address of the OEF Agent")
    parser.add_argument("--oef-port", default=3333, help="TCP/IP port of the OEF Agent")
    # parser.add_argument("--gui", action="store_true", help="Show the GUI.")

    return parser.parse_args()


class Game(object):

    def __init__(self, money_endowment: int, instances_per_good: int, nb_agents: int):
        self.money_endowment = money_endowment
        self.instances_per_good = instances_per_good
        self.nb_agents = nb_agents


class ControllerHandler(object):

    def __init__(self, controller: 'ControllerAgent'):
        self.controller = controller

    def handle(self, msg: bytes):
        """Handle a simple message coming from other agents."""
        message = self.decode(msg)  # type: Request
        self.dispatch(message)

    def dispatch(self, request: Request):
        """Dispatch the request to the right handler"""
        if request.method == Methods.REGISTER:
            self.controller.register_tac_agent(request.origin)
        else:
            raise Exception("Something wrong happened.")

    def decode(self, msg: bytes) -> Request:
        """From bytes to a Request message"""
        # TODO make checks about the fields (maybe using jsonschema package)
        # TODO error handling!
        body = json.load(msg)
        method = body["method"]
        origin = body["origin"]
        if method == Methods.REGISTER.value:
            message = Request(Methods.REGISTER, origin)
        else:
            raise Exception("Method not recognized")
        return message


class ControllerAgent(TacAgent):
    CONTROLLER_DATAMODEL = DataModel("tac", [])
    CONTROLLER_DESC = Description({}, data_model=CONTROLLER_DATAMODEL)

    def __init__(self, public_key="controller", oef_addr="127.0.0.1", oef_port=3333,
                 money_endowment: int = 20, nb_goods: int = 5, **kwargs):
        super().__init__(public_key, oef_addr, oef_port, **kwargs)

        self.money_endowment = money_endowment
        self.nb_goods = nb_goods

        self.registered_agents = set()  # type: Set[str]

        self.game = None  # type: Optional[Game]
        self.handler = ControllerHandler(self)

    def register(self):
        self.register_service(0, self.CONTROLLER_DESC)

    def on_message(self, msg_id: int, dialogue_id: int, origin: str, content: bytes):
        logger.debug("on_message: {}, {}, {}".format(msg_id, dialogue_id, origin))
        self.handler.handle(content)

    def register_tac_agent(self, public_key: str):
        if public_key in self.registered_agents:
            logger.error("Agent already registered: {}".format(public_key))
        else:
            logger.debug("Agent registered: {}".format(public_key))
            self.registered_agents.add(public_key)


def main():
    args = parse_arguments()
    agent = ControllerAgent(public_key=args.public_key, oef_addr=args.oef_addr, oef_port=args.oef_port)

    agent.connect()
    agent.register()
    agent.run()


if __name__ == '__main__':
    main()


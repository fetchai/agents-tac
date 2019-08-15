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

"""This script waits until the OEF is up and running."""

import logging

from oef.agents import OEFAgent
from oef.core import AsyncioCore

logger = logging.getLogger(__name__)


class OEFHealthCheck(object):
    """A health check class."""

    def __init__(self, addr: str, port: int):
        """
        Initialize.

        :param addr: IP address of the OEF node.
        :param port: Port of the OEF node.
        """
        self.addr = addr
        self.port = port

    def run(self) -> bool:
        """
        Run the check.

        :return:
        """
        result = False
        try:
            # import pdb; pdb.set_trace()
            pbk = 'check'
            print("Connecting to {}:{}".format(self.addr, self.port))
            core = AsyncioCore(logger=logger)
            core.run_threaded()
            agent = OEFAgent(pbk, oef_addr=self.addr, oef_port=self.port, core=core)
            agent.connect()
            agent.disconnect()
            print("OK!")
            result = True
            return result
        except Exception as e:
            print(str(e))
            return result

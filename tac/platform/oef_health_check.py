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

import argparse
import asyncio
import logging
from threading import Timer
from typing import Optional

from oef.agents import AsyncioCore, OEFAgent

logger = logging.getLogger(__name__)


parser = argparse.ArgumentParser("oef_healthcheck", description=__doc__)
parser.add_argument(
    "--oef-addr", default="127.0.0.1", type=str, help="TCP/IP address of the OEF Agent"
)
parser.add_argument(
    "--oef-port", default=10000, type=int, help="TCP/IP port of the OEF Agent"
)


class OEFHealthCheck(object):
    """A health check class."""

    def __init__(
        self,
        oef_addr: str,
        oef_port: int,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ):
        """
        Initialize.

        :param oef_addr: IP address of the OEF node.
        :param oef_port: Port of the OEF node.
        """
        self.oef_addr = oef_addr
        self.oef_port = oef_port

        self._result = False
        self._stop = False
        self._core = AsyncioCore()
        self.agent = OEFAgent(
            "check", core=self._core, oef_addr=self.oef_addr, oef_port=self.oef_port
        )
        self.agent.on_connect_success = self.on_connect_ok
        self.agent.on_connection_terminated = self.on_connect_terminated
        self.agent.on_connect_failed = self.exception_handler

    def exception_handler(self, url=None, ex=None):
        """Handle exception during a connection attempt."""
        print("An error occurred. Exception: {}".format(ex))
        self._stop = True

    def on_connect_ok(self, url=None):
        """Handle a successful connection."""
        print("Connection OK!")
        self._result = True
        self._stop = True

    def on_connect_terminated(self, url=None):
        """Handle a connection failure."""
        print("Connection terminated.")
        self._stop = True

    def run(self) -> bool:
        """
        Run the check, asynchronously.

        :return: True if the check is successful, False otherwise.
        """
        self._result = False
        self._stop = False

        def stop_connection_attempt(self):
            if self.agent.state == "connecting":
                self.agent.state = "failed"

        t = Timer(1.5, stop_connection_attempt, args=(self,))

        try:
            print("Connecting to {}:{}...".format(self.oef_addr, self.oef_port))
            self._core.run_threaded()

            t.start()
            self._result = self.agent.connect()
            self._stop = True

            if self._result:
                print("Connection established. Tearing down connection...")
                self.agent.disconnect()
                t.cancel()
            else:
                print("A problem occurred. Exiting...")

        except Exception as e:
            print(str(e))
        finally:
            t.join(1.0)
            self.agent.stop()
            self.agent.disconnect()
            self._core.stop()
            return self._result


def main(oef_addr, oef_port):
    """Launch the health check."""
    oef_health_check = OEFHealthCheck(oef_addr, oef_port)
    return oef_health_check.run()


if __name__ == "__main__":
    args = parser.parse_args()
    main(args.oef_addr, args.oef_port)

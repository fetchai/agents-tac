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
from typing import Optional

from aea.crypto.base import Crypto
from aea.channel.oef import OEFMailBox
from oef.core import AsyncioCore, Connection

logger = logging.getLogger(__name__)


parser = argparse.ArgumentParser("oef_healthcheck", description=__doc__)
parser.add_argument("--oef-addr", default="127.0.0.1", type=str, help="TCP/IP address of the OEF Agent")
parser.add_argument("--oef-port", default=10000, type=int, help="TCP/IP port of the OEF Agent")


class OEFHealthCheck(object):
    """A health check class."""

    def __init__(self, oef_addr: str, oef_port: int, loop: Optional[asyncio.AbstractEventLoop] = None):
        """
        Initialize.

        :param oef_addr: IP address of the OEF node.
        :param oef_port: Port of the OEF node.
        """
        self.oef_addr = oef_addr
        self.oef_port = oef_port

        self._result = False
        self._stop = False
        self._conn = None
        self._loop = asyncio.get_event_loop() if loop is None else loop
        self._loop.set_exception_handler(self.exception_handler)
        self._core = AsyncioCore(loop=self._loop)

    def exception_handler(self, loop, d):
        """Handle exception during a connection attempt."""
        print("An error occurred. Details: {}".format(d))
        self._stop = True

    def on_connect_ok(self, conn=None, url=None, ex=None, conn_name=None):
        """Handle a successful connection."""
        print("Connection OK!")
        self._result = True
        self._stop = True

    def on_connect_fail(self, conn=None, url=None, ex=None, conn_name=None):
        """Handle a connection failure."""
        print("Connection failed. {}".format(ex))
        self._result = False
        self._stop = True

    async def _run(self) -> bool:
        """
        Run the check, asynchronously.

        :return: True if the check is successful, False otherwise.
        """
        self._result = False
        self._stop = False
        pbk = 'check'
        seconds = 3.0
        try:
            print("Connecting to {}:{}...".format(self.oef_addr, self.oef_port))

            self._conn = Connection(self._core)
            self._conn.connect(url="127.0.0.1:10000", success=self.on_connect_ok,
                               failure=self.on_connect_fail,
                               public_key=pbk)

            while not self._stop and seconds > 0:
                await asyncio.sleep(1.0)
                seconds -= 1.0

            if self._result:
                print("Connection established. Tearing down connection...")
                self._core.call_soon_async(self._conn.do_stop)
                await asyncio.sleep(1.0)
            else:
                print("A problem occurred. Exiting...")

        except Exception as e:
            print(str(e))
        finally:
            return self._result

    def run(self) -> bool:
        """Run the check.

        :return: True if the check is successful, False otherwise.
        """
        return self._loop.run_until_complete(self._run())


def main(oef_addr, oef_port):
    """Launch the health check."""
    oef_health_check = OEFHealthCheck(oef_addr, oef_port)
    return oef_health_check.run()


if __name__ == "__main__":
    args = parser.parse_args()
    main(args.oef_addr, args.oef_port)

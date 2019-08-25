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
import logging

from aea.crypto.base import Crypto
from aea.channel.oef import OEFMailBox

logger = logging.getLogger(__name__)


parser = argparse.ArgumentParser("oef_healthcheck", description=__doc__)
parser.add_argument("--oef-addr", default="127.0.0.1", type=str, help="TCP/IP address of the OEF Agent")
parser.add_argument("--oef-port", default=10000, type=int, help="TCP/IP port of the OEF Agent")


class OEFHealthCheck(object):
    """A health check class."""

    def __init__(self, oef_addr: str, oef_port: int):
        """
        Initialize.

        :param oef_addr: IP address of the OEF node.
        :param oef_port: Port of the OEF node.
        """
        crypto = Crypto()
        self.mailbox = OEFMailBox(crypto.public_key, oef_addr=oef_addr, oef_port=oef_port)
        self.oef_addr = oef_addr
        self.oef_port = oef_port

    def run(self) -> bool:
        """
        Run the check.

        :return:
        """
        result = False
        try:
            print("Connecting to {}:{}".format(self.oef_addr, self.oef_port))
            self.mailbox.connect()
            self.mailbox.disconnect()
            print("OK!")
            result = True
            return result
        except Exception as e:
            print(str(e))
            return result


def main(oef_addr, oef_port):
    """Launch the health check."""
    oef_health_check = OEFHealthCheck(oef_addr, oef_port)
    return oef_health_check.run()


if __name__ == "__main__":
    args = parser.parse_args()
    main(args.oef_addr, args.oef_port)

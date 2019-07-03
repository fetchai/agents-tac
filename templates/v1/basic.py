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

"""Template agent, no modification required."""

import argparse
import logging

import tac
from tac.agents.v1.base.strategy import RegisterAs
from tac.agents.v1.examples.baseline import BaselineAgent

logger = logging.getLogger(__name__)


def parse_arguments():
    """Arguments parsing."""
    parser = argparse.ArgumentParser("basic-agent", description="Launch my agent.")
    parser.add_argument("--name", default="my_baseline_agent", help="Name of the agent.")
    parser.add_argument("--oef-addr", default="127.0.0.1", help="TCP/IP address of the OEF Agent")
    parser.add_argument("--oef-port", default=10000, help="TCP/IP port of the OEF Agent")
    parser.add_argument("--agent-timeout", type=float, default=1.0, help="The time in (fractions of) seconds to time out an agent between act and react.")
    parser.add_argument("--max-reactions", type=int, default=100, help="The maximum number of reactions (messages processed) per call to react.")
    parser.add_argument("--register-as", choices=['seller', 'buyer', 'both'], default='both', help="The string indicates whether the baseline agent registers as seller, buyer or both on the oef.")
    parser.add_argument("--search-for", choices=['sellers', 'buyers', 'both'], default='both', help="The string indicates whether the baseline agent searches for sellers, buyers or both on the oef.")
    parser.add_argument("--is-world-modeling", type=bool, default=False, help="Whether the agent uses a workd model or not.")
    parser.add_argument("--services-interval", type=int, default=10, help="The number of seconds to wait before doing another search.")
    parser.add_argument("--pending-transaction-timeout", type=int, default=30, help="The timeout in seconds to wait for pending transaction/negotiations.")
    parser.add_argument("--private-key-pem", type=str, default=None, help="Path to a file containing a private key in PEM format.")
    parser.add_argument("--rejoin", action="store_true", default=False, help="Whether the agent is joining a running TAC.")
    parser.add_argument("--gui", action="store_true", help="Show the GUI.")
    parser.add_argument("--visdom_addr", type=str, default="localhost", help="IP address to the Visdom server")
    parser.add_argument("--visdom_port", type=int, default=8097, help="Port of the Visdom server")

    return parser.parse_args()


if __name__ == '__main__':
    args = parse_arguments()
    tac.agents.v1.examples.baseline.main(**args.__dict__)

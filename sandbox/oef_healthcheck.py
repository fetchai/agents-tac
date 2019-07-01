#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""This script waits until the OEF is up and running"""

import argparse
import asyncio

import oef.agents

parser = argparse.ArgumentParser("oef_healthcheck", description=__doc__)
parser.add_argument("addr", type=str, help="IP address of the OEF node.")
parser.add_argument("port", type=int, help="Port of the OEF node.")

if __name__ == '__main__':
    try:
        args = parser.parse_args()
        host = args.addr
        port = args.port
        pbk = 'check'
        print("Connecting to {}:{}".format(host, port))
        agent = oef.agents.OEFAgent(pbk, host, port, loop=asyncio.get_event_loop())
        agent.connect()
        agent.disconnect()
        print("OK!")
        exit(0)
    except Exception as e:
        print(str(e))
        exit(1)

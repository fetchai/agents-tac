import asyncio

import oef.agents

import sys

if __name__ == '__main__':
    try:
        host = sys.argv[1]
        port = sys.argv[2]
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

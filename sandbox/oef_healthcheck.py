import asyncio

import oef.agents


if __name__ == '__main__':
    agent = oef.agents.OEFAgent('healthcheck-agent','127.0.0.1', 3333, loop=asyncio.get_event_loop())
    agent.connect()
    agent.disconnect()
    exit(0)

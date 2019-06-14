import argparse
from typing import Optional

from tac.agents.v2.base.participant_agent import ParticipantAgent
from tac.agents.v2.base.strategy import Strategy, SearchFor, RegisterAs
from tac.agents.v2.examples.strategy import BaselineStrategy
from tac.gui.dashboards.agent import AgentDashboard
from tac.gui.dashboards.base import start_visdom_server


class BaselineAgent(ParticipantAgent):

    def __init__(self, name: str, oef_addr: str, oef_port: int, strategy: Strategy, search_interval: int = 10, pending_transaction_timeout: int = 30, dashboard: Optional[AgentDashboard] = None):
        super().__init__(name, oef_addr, oef_port, strategy, search_interval, pending_transaction_timeout, dashboard)


def _parse_arguments():
    parser = argparse.ArgumentParser("BaselineAgent", description="Launch the BaselineAgent.")
    parser.add_argument("--name", type=str, default="baseline_agent", help="Name of the agent.")
    parser.add_argument("--gui", action="store_true", help="Show the GUI.")
    parser.add_argument("--visdom_addr", type=str, default="localhost", help="Show the GUI.")
    parser.add_argument("--visdom_port", type=int, default=8097, help="Show the GUI.")
    parser.add_argument("--search-interval", type=int, default=10, help="The number of seconds to wait before doing another search.")
    parser.add_argument("--pending-transaction-timeout", type=int, default=30, help="The timeout in seconds to wait for pending transaction/negotiations.")
    return parser.parse_args()


if __name__ == '__main__':

    arguments = _parse_arguments()
    process = None
    if arguments.gui:
        process = start_visdom_server()
        dashboard = AgentDashboard(agent_name=arguments.name, env_name=arguments.name)
    else:
        process = None
        dashboard = None

    strategy = BaselineStrategy(register_as=RegisterAs.BOTH, search_for=SearchFor.BOTH, is_world_modeling=False)
    agent = BaselineAgent(arguments.name, "127.0.0.1", 3333, strategy, arguments.search_interval, arguments.pending_transaction_timeout, dashboard)

    try:
        agent.start()
    finally:
        if not agent.liveness.is_stopped:
            agent.stop()
            agent.game_instance.lock_manager.stop()
        if process is not None:
            process.terminate()

import argparse

from tac.agents.v2.base.participant_agent import ParticipantAgent
from tac.agents.v2.base.strategy import Strategy, SearchFor, RegisterAs
from tac.agents.v2.examples.strategy import BaselineStrategy


class BaselineAgent(ParticipantAgent):

    def __init__(self, name: str, oef_addr: str, oef_port: int, strategy: Strategy, services_interval: int = 10, pending_transaction_timeout: int = 30):
        super().__init__(name, oef_addr, oef_port, strategy, services_interval, pending_transaction_timeout)


def _parse_arguments():
    parser = argparse.ArgumentParser("BaselineAgent", description="Launch the BaselineAgent.")
    parser.add_argument("--name", default="baseline_agent", help="Name of the agent.")
    return parser.parse_args()


if __name__ == '__main__':

    arguments = _parse_arguments()

    strategy = BaselineStrategy(register_as=RegisterAs.BOTH, search_for=SearchFor.BOTH, is_world_modeling=False)
    agent = BaselineAgent(arguments.name, "127.0.0.1", 3333, strategy, 10, 30)
    try:
        agent.start()
    finally:
        agent.stop()
        agent.game_instance.lock_manager.stop()

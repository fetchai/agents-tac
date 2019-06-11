import argparse

from tac.agents.v2.base.participant_agent import ParticipantAgent


class BaselineAgent(ParticipantAgent):

    def __init__(self, name: str, oef_addr: str, oef_port: int = 3333, register_as: str = 'both', search_for: str = 'both', is_world_modeling: bool = False, pending_transaction_timeout: int = 30):
        super().__init__(name, oef_addr, oef_port, register_as, search_for, is_world_modeling, pending_transaction_timeout)


def _parse_arguments():
    parser = argparse.ArgumentParser("BaselineAgent", description="Launch the BaselineAgent.")
    parser.add_argument("--name", default="baseline_agent", help="Name of the agent.")
    return parser.parse_args()


if __name__ == '__main__':

    arguments = _parse_arguments()

    agent = BaselineAgent(arguments.name, "127.0.0.1", 3333, False)
    try:
        agent.start()
    finally:
        agent.stop()

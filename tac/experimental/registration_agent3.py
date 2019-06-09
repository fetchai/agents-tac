import argparse

from tac.experimental.core.tac.participant_agent import ParticipantAgent


class TACRegistrationAgent(ParticipantAgent):

    def __init__(self, name: str, oef_addr: str, oef_port: int = 3333, is_world_modeling: bool = False):
        super().__init__(name, oef_addr, oef_port, is_world_modeling)


def _parse_arguments():
    parser = argparse.ArgumentParser("TACRegistrationAgent", description="Launch the TACRegistrationAgent agent.")
    parser.add_argument("--name", default="tac_reg_agent", help="Name of the agent.")
    return parser.parse_args()


if __name__ == '__main__':

    arguments = _parse_arguments()

    agent = TACRegistrationAgent(arguments.name, "127.0.0.1", 3333, False)
    try:
        agent.start()
    finally:
        agent.stop()

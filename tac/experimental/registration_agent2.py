from tac.experimental.core2 import TACParticipantAgent


class TACRegistrationAgent(TACParticipantAgent):

    def __init__(self, name: str, oef_addr: str, oef_port: int = 10000, is_world_modeling: bool = False):
        super().__init__(name, oef_addr, oef_port, is_world_modeling)


if __name__ == '__main__':

    agent = TACRegistrationAgent("tac_reg_agent", "127.0.0.1", 10000, False)
    try:
        agent.start()
    finally:
        agent.stop()

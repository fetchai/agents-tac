# -*- coding: utf-8 -*-
from oef.messages import DialogueErrorMessage, OEFErrorMessage

from tac.experimental.core1 import TACParticipantAgent, Dialogue
from tac.platform.protocol import Error, StateUpdate, TransactionConfirmation


class TACRegistrationAgent(TACParticipantAgent):

    def on_new_dialogue(self, msg) -> Dialogue:
        pass

    def on_oef_error(self, oef_error: OEFErrorMessage):
        pass

    def on_dialogue_error(self, dialogue_error: DialogueErrorMessage):
        pass

    def on_start(self) -> None:
        pass

    def on_transaction_confirmed(self, tx_confirmation: TransactionConfirmation) -> None:
        pass

    def on_state_update(self, agent_state: StateUpdate) -> None:
        pass

    def on_tac_error(self, error: Error) -> None:
        pass


if __name__ == '__main__':

    agent = TACRegistrationAgent("tac_reg_agent", "127.0.0.1", 3333, False)
    try:
        agent.start()
    finally:
        agent.stop()

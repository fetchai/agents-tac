# -*- coding: utf-8 -*-
import asyncio
from abc import abstractmethod, ABC
from asyncio import AbstractEventLoop
from queue import Queue
from threading import Thread
from typing import List, Union, Set, Optional, Any, Dict

from oef.agents import OEFAgent
from oef.messages import PROPOSE_TYPES, CFP_TYPES, CFP, Decline, Propose, Accept, Message
from tac.game import AgentState, WorldState
from tornado.platform import asyncio

from tac.agents.baseline import LockManager
from tac.core import NegotiationAgent
from tac.protocol import Error, TransactionConfirmation

Action = Any


class DialogueLabel:
    """Identifier for dialogues."""

    def __init__(self, dialogue_id: int, agent_pbk: str):
        """
        Initialize a dialogue label.
        :param dialogue_id: the id of the dialogue.
        :param agent_pbk: the interlocutor agent's public key.
        """
        self._dialogue_id = dialogue_id
        self._agent_pbk = agent_pbk

    @property
    def dialogue_id(self) -> int:
        return self._dialogue_id

    @property
    def agent_pbk(self) -> str:
        return self._agent_pbk

    def __eq__(self, other):
        if type(other) == DialogueLabel:
            return self._dialogue_id == other.dialogue_id and self._agent_pbk == other.agent_pbk
        else:
            return False

    def __hash__(self):
        return hash((self.dialogue_id, self.agent_pbk))


class AgentMessage:

    def __init__(self, dialogue_label: DialogueLabel, content: Any):
        self.dialogue_label = dialogue_label
        self.content = content


class Crypto(object):
    pass


class MailBox(OEFAgent):

    def __init__(self, public_key: str, oef_addr: str, oef_port: int = 3333,
                 loop: Optional[AbstractEventLoop] = None, crypto: Optional[Crypto] = None):
        super().__init__(public_key, oef_addr, oef_port, loop)
        self.queue = Queue()
        self.crypto = crypto

        self._mail_box_thread = None  # type: Optional[Thread]

    def on_message(self, msg_id: int, dialogue_id: int, origin: str, content: bytes):
        self.queue.put(Message(msg_id, dialogue_id, origin, content))

    def on_cfp(self, msg_id: int, dialogue_id: int, origin: str, target: int, query: CFP_TYPES):
        self.queue.put(CFP(msg_id, dialogue_id, origin, target, query))

    def on_propose(self, msg_id: int, dialogue_id: int, origin: str, target: int, proposals: PROPOSE_TYPES):
        self.queue.put(Propose(msg_id, dialogue_id, origin, target, proposals))

    def on_accept(self, msg_id: int, dialogue_id: int, origin: str, target: int):
        self.queue.put(Accept(msg_id, dialogue_id, origin, target))

    def on_decline(self, msg_id: int, dialogue_id: int, origin: str, target: int):
        self.queue.put(Decline(msg_id, dialogue_id, origin, target))

    def is_running(self) -> bool:
        return self._mail_box_thread is None

    def start(self) -> None:
        self._mail_box_thread = Thread(target=super().run)
        self._mail_box_thread.start()

    def stop(self) -> None:
        self._loop.call_soon_threadsafe(super().stop)
        self.halt_loop()
        self._mail_box_thread.join()

class InBox(object):

    def __init__(self, mail_box: MailBox):
        self._mail_box = mail_box

    def get(self) -> AgentMessage:
        return self._mail_box.queue.get()


class OutBox(object):

    def __init__(self, mail_box: MailBox):
        self._mail_box = mail_box

    def send_error(self):
        pass

    def send_message(self, msg):
        pass


class Dialogue:

    def __init__(self, agent: 'Agent', dialogue_label: DialogueLabel):
        self.agent = agent
        self.dialogue_label = dialogue_label
        self.messages = []  # type: List[AgentMessage]


class Dialogues:

    def __init__(self):
        self.dialogues = {}  # type: Dict[DialogueLabel, Dialogue]

    def is_dialogue_registered(self, dialogue_label):
        return dialogue_label in self.dialogues

    def get_dialogue(self, dialogue_label: DialogueLabel) -> Dialogue:
        return self.dialogues[dialogue_label]

    def register_dialogue(self, dialogue: Dialogue):
        self.dialogues[dialogue.dialogue_label] = dialogue


class ProtocolInterface:

    @abstractmethod
    def check_message(self, dialogue: Dialogue, msg: AgentMessage) -> bool:
        pass


class BehaviourInterface:

    @abstractmethod
    def dispatch_to_handler(self, dialogue: Dialogue, msg: AgentMessage) -> Optional[Action]:
        pass


class FIPAProtocol(ProtocolInterface):

    def check_message(self, dialogue: Dialogue, msg: AgentMessage) -> bool:
        if isinstance(msg, Message):
            return self.check_simple_message(msg)
        # elif CFP
        # elif Propose
        # ...
        else:
            return False

    def check_simple_message(self, dialogue: Dialogue, msg: AgentMessage):
        return True


class BaselineBehaviour(BehaviourInterface):

    def dispatch_to_handler(self, dialogue: Dialogue, msg: Message) -> Optional[Action]:
        if isinstance(msg, Message):
            return self.on_message(msg)
        # elif
        else:
            return None  # or NullAction

    def on_message(self, msg):
        pass


class Agent(ABC, ProtocolInterface, BehaviourInterface):

    def __init__(self, public_key: str, oef_addr: str, oef_port: int = 3333):
        self.crypto = Crypto()
        self.mail_box = MailBox(public_key, oef_addr, oef_port, crypto=self.crypto)

        self.in_box = InBox(self.mail_box)
        self.out_box = OutBox(self.mail_box)
        self.dialogues = Dialogues()
        self.agent_state = AgentState()
        self.world_state = WorldState()

    def run(self):
        msg = self.in_box.get()  # type: AgentMessage

        if self.dialogues.is_dialogue_registered(msg.dialogue_label):
            dialogue = self.dialogues.get_dialogue(msg.dialogue_label)
        else:
            dialogue = Dialogue(self, msg.dialogue_label)

        if not self.check_message(dialogue, msg):
            self.out_box.send_error()
        else:
            response = self.dispatch_to_handler(dialogue, msg)
            self.out_box.send_message(response)


class TACNegotiationAgent(Agent, FIPAProtocol, BaselineBehaviour):
    pass

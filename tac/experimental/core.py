# -*- coding: utf-8 -*-
import logging
from abc import abstractmethod, ABC
from asyncio import AbstractEventLoop
from enum import Enum
from queue import Queue
from threading import Thread
from typing import List, Optional, Any, Dict, Union

from oef.agents import OEFAgent
from oef.messages import PROPOSE_TYPES, CFP_TYPES, CFP, Decline, Propose, Accept, Message as SimpleMessage, \
    SearchResult, \
    OEFErrorOperation, OEFErrorMessage, DialogueErrorMessage, AgentMessage
from oef.query import Query, Constraint, GtEq

from tac.game import AgentState, WorldState, GameConfiguration
from tac.protocol import Error, TransactionConfirmation, StateUpdate, Response, GameData, Cancelled

logger = logging.getLogger(__name__)

Action = Any
OEFMessage = Union[SearchResult, OEFErrorMessage, DialogueErrorMessage]
ControllerResponse = Response
Message = Union[OEFMessage, AgentMessage]


def is_oef_message(msg: Message) -> bool:
    msg_type = type(msg)
    return msg_type in {SearchResult, OEFErrorMessage, DialogueErrorMessage}


def is_controller_message(msg: Message) -> bool:
    msg_type = type(msg)
    if not isinstance(msg_type, SimpleMessage):
        return False

    try:
        msg: SimpleMessage
        byte_content = msg.msg
        Response.from_pb(byte_content, "")
    except Exception:
        return False

    return True


class GamePhase(Enum):
    PRE_GAME = 'pre_game'
    GAME_SETUP = 'game_setup'
    GAME = 'game'
    POST_GAME = 'post_game'


class ControllerInterface:
    """
    This interface contains the methods to interact with the ControllerAgent.
    """

    @abstractmethod
    def on_start(self) -> None:
        """
        On start of the competition, do the setup.

        :return: None
        """

    @abstractmethod
    def on_cancelled(self) -> None:
        """
        Handle the cancellation of the competition from the TAC controller.

        :return: None
        """

    @abstractmethod
    def on_search_results(self, search_id: int, agents: List[str]) -> None:
        """
        Handle search results.

        :return: None
        """

    @abstractmethod
    def on_transaction_confirmed(self, tx_confirmation: TransactionConfirmation) -> None:
        """
        On Transaction confirmed handler.

        :param tx_confirmation: the transaction confirmation

        :return: None
        """

    @abstractmethod
    def on_state_update(self, agent_state: StateUpdate) -> None:
        """
        On receiving the agent state update.

        :param agent_state: the current state of the agent in the competition.
        :return: None
        """

    @abstractmethod
    def on_tac_error(self, error: Error) -> None:
        """
        Handle error messages from the TAC controller.

        :return: None
        """


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

        self.search_id = 1

        self._mail_box_thread = None  # type: Optional[Thread]

    def on_message(self, msg_id: int, dialogue_id: int, origin: str, content: bytes):
        try:
            response = Response.from_pb(content, self.public_key)
            self.queue.put(response)
        except Exception:
            self.queue.put(SimpleMessage(msg_id, dialogue_id, origin, content))

    def on_cfp(self, msg_id: int, dialogue_id: int, origin: str, target: int, query: CFP_TYPES):
        self.queue.put(CFP(msg_id, dialogue_id, origin, target, query))

    def on_propose(self, msg_id: int, dialogue_id: int, origin: str, target: int, proposals: PROPOSE_TYPES):
        self.queue.put(Propose(msg_id, dialogue_id, origin, target, proposals))

    def on_accept(self, msg_id: int, dialogue_id: int, origin: str, target: int):
        self.queue.put(Accept(msg_id, dialogue_id, origin, target))

    def on_decline(self, msg_id: int, dialogue_id: int, origin: str, target: int):
        self.queue.put(Decline(msg_id, dialogue_id, origin, target))

    def on_search_result(self, search_id: int, agents: List[str]):
        self.queue.put(SearchResult(search_id, agents))

    def on_oef_error(self, answer_id: int, operation: OEFErrorOperation):
        self.queue.put(OEFErrorMessage(answer_id, operation))

    def on_dialogue_error(self, answer_id: int, dialogue_id: int, origin: str):
        self.queue.put(DialogueErrorMessage(answer_id, dialogue_id, origin))

    def search_services(self, query: Query) -> int:
        self.search_id = self.search_id + 1
        super().search_services(self.search_id, query)
        return self.search_id

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
    def check_message(self, msg: AgentMessage) -> bool:
        pass


class BehaviourInterface:

    @abstractmethod
    def dispatch_to_handler(self, msg: AgentMessage) -> Optional[Action]:
        pass


class Dialogue(ProtocolInterface, BehaviourInterface):

    def __init__(self, agent: 'Agent', dialogue_label: DialogueLabel):
        self.agent = agent
        self.dialogue_label = dialogue_label
        self.messages = []  # type: List[AgentMessage]


class FIPAProtocol(ProtocolInterface):

    def check_message(self, msg: AgentMessage) -> bool:
        if isinstance(msg, SimpleMessage):
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


class TACGameInstance:

    def __init__(self, is_world_modeling: bool = False):
        self._controller_pbk = None  # type: Optional[str]
        self._game_configuration = None  # type: Optional[GameConfiguration]
        self._initial_agent_state = None  # type: Optional[AgentState]
        self._agent_state = None  # type: Optional[AgentState]
        self._is_world_modeling = is_world_modeling
        self._world_state = None  # type: Optional[WorldState]
        self.game_phase = GamePhase.PRE_GAME

    def init(self, game_data: GameData, controller_pbk: str):
        # populate data structures about the started competition
        self._controller_pbk = controller_pbk
        self._game_configuration = GameConfiguration(game_data.nb_agents, game_data.nb_goods, game_data.tx_fee,
                                                     game_data.agent_pbks, game_data.good_pbks)
        self._initial_agent_state = AgentState(game_data.money, game_data.endowment, game_data.utility_params)
        self._agent_state = AgentState(game_data.money, game_data.endowment, game_data.utility_params)
        if self.is_world_modeling:
            opponent_pbks = self.game_configuration.agent_pbks
            opponent_pbks.remove(game_data.public_key)
            self._world_state = WorldState(opponent_pbks, self.game_configuration.good_pbks, self.initial_agent_state)

    def reset(self):
        self._controller_pbk = None  # type: Optional[str]
        self._game_configuration = None  # type: Optional[GameConfiguration]
        self._initial_agent_state = None  # type: Optional[AgentState]
        self._agent_state = None  # type: Optional[AgentState]
        self._world_state = None  # type: Optional[WorldState]
        self.game_phase = GamePhase.PRE_GAME

    @property
    def game_configuration(self):
        return self._game_configuration

    @property
    def initial_agent_state(self):
        return self._initial_agent_state

    @property
    def agent_state(self):
        return self._agent_state

    @property
    def world_state(self):
        return self._world_state

    @property
    def is_world_modeling(self):
        return self._is_world_modeling


class TACParticipantAgent(ABC, ControllerInterface):

    def __init__(self, name: str, oef_addr: str, oef_port: int = 3333, is_world_modeling: bool = False):
        self.crypto = Crypto()
        self.mail_box = MailBox(name, oef_addr, oef_port, crypto=self.crypto)

        self.in_box = InBox(self.mail_box)
        self.out_box = OutBox(self.mail_box)

        self.dialogues = Dialogues()

        self._game_instance = TACGameInstance(is_world_modeling)  # type:  Optional[TACGameInstance]

        self._stopped = True  # type: bool

    @property
    def name(self) -> str: return self.mail_box.public_key
    @property
    def game_instance(self): return self._game_instance

    @property
    def game_phase(self): return self._game_instance.game_phase
    @game_phase.setter
    def game_phase(self, value: GamePhase): self._game_instance.game_phase = value

    def stop(self):
        self._stopped = True

    def start(self):

        self._stopped = False

        while not self._stopped:
            msg = self.in_box.get()  # type: Message

            if is_oef_message(msg):
                self.handle_oef_message(msg)
            elif is_controller_message(msg):
                msg: SimpleMessage
                self.handle_controller_message(msg)
            else:
                self.handle_dialogue_message(msg)

    def handle_oef_message(self, msg: Union[SearchResult, OEFErrorMessage, DialogueErrorMessage]):
        if isinstance(msg, SearchResult):
            self.on_search_result(msg)
        elif isinstance(msg, OEFErrorMessage):
            self.on_oef_error(msg)
        elif isinstance(msg, DialogueErrorMessage):
            self.on_dialogue_error(msg)
        else:
            logger.warning("OEF Message type not recognized.")

    def handle_controller_message(self, msg: SimpleMessage):
        response = Response.from_pb(msg.msg, self.name)
        try:
            if isinstance(response, Error):
                self.on_tac_error(response)

            elif self.game_phase == GamePhase.PRE_GAME:
                raise ValueError("We do not expect a controller message in the pre-game phase.")
            elif self.game_phase == GamePhase.GAME_SETUP:
                if isinstance(response, GameData):
                    self._game_instance.init(response, msg.destination)
                    self.game_phase = GamePhase.GAME
                    self.on_start()
            elif self.game_phase == GamePhase.GAME:
                if isinstance(response, TransactionConfirmation):
                    self.on_transaction_confirmed(response)
                elif isinstance(response, Cancelled):
                    self.game_phase = GamePhase.POST_GAME
                    self.on_cancelled()
                elif isinstance(response, StateUpdate):
                    self.on_state_update(response)
            elif self.game_phase == GamePhase.POST_GAME:
                pass
        except ValueError as e:
            logger.warning(str(e))

    def handle_dialogue_message(self, msg: AgentMessage):
        if self.dialogues.is_dialogue_registered(msg.dialogue_label):
            dialogue = self.dialogues.get_dialogue(msg.dialogue_label)
        else:
            dialogue = self.on_new_dialogue(msg)

        if not dialogue.check_message(msg):
            self.out_box.send_error()
        else:
            response = dialogue.dispatch_to_handler(msg)
            self.out_box.send_message(response)

    @abstractmethod
    def on_new_dialogue(self, msg) -> Dialogue:
        """Given a new message, create a Dialogue object that specifies:
        - the protocol rules that messages must follow;
        - how the agent behaves in this dialogue.
        """

    @abstractmethod
    def on_search_result(self, search_result: SearchResult):
        """Process a search result from the OEF."""

    @abstractmethod
    def on_oef_error(self, oef_error: OEFErrorMessage):
        """Handle an OEF error message."""

    @abstractmethod
    def on_dialogue_error(self, dialogue_error: DialogueErrorMessage):
        """Handler a dialogue error message"""

    def search_for_tac(self) -> None:
        """
        Search for active TAC Controller.

        We assume that the controller is registered as a service with the 'tac' data model
        and with an attribute version = 1.

        :return: None
        """
        query = Query([Constraint("version", GtEq(1))])
        self.mail_box.search_services(query)

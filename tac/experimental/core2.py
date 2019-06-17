# -*- coding: utf-8 -*-
import asyncio
import logging
from abc import abstractmethod
from enum import Enum
from typing import List, Optional, Any, Dict, Union, Set

from oef.messages import CFP, Decline, Propose, Accept, Message as SimpleMessage, \
    SearchResult, OEFErrorMessage, DialogueErrorMessage
from oef.query import Query, Constraint, GtEq

from tac.agents.v2.mail import MailBox, FIPAMailBox, InBox, OutBox, OutContainer
from tac.platform.game import AgentState, WorldState, GameConfiguration
from tac.helpers.crypto import Crypto
from tac.platform.protocol import Error, TransactionConfirmation, StateUpdate, Response, GameData, Cancelled, Register

logger = logging.getLogger(__name__)

Action = Any
OEFMessage = Union[SearchResult, OEFErrorMessage, DialogueErrorMessage]
ControllerMessage = SimpleMessage
AgentMessage = Union[SimpleMessage, CFP, Propose, Accept, Decline]
Message = Union[OEFMessage, ControllerMessage, AgentMessage]


def is_oef_message(msg: Message) -> bool:
    msg_type = type(msg)
    return msg_type in {SearchResult, OEFErrorMessage, DialogueErrorMessage}


def is_controller_message(msg: Message, crypto: Crypto) -> bool:
    if not isinstance(msg, SimpleMessage):
        return False

    try:
        msg: SimpleMessage
        byte_content = msg.msg
        sender_pbk = msg.destination  # now the origin is the destination!
        Response.from_pb(byte_content, sender_pbk, crypto)
    except Exception:
        return False

    return True


class GamePhase(Enum):
    PRE_GAME = 'pre_game'
    GAME_SETUP = 'game_setup'
    GAME = 'game'
    POST_GAME = 'post_game'


class Liveness:
    """
    Determines the liveness of the agent.
    """
    def __init__(self):
        self._is_stopped = True

    @property
    def is_stopped(self):
        return self._is_stopped


class TACGameInstance:
    """
    The TACGameInstance maintains state of the game from the agent's perspective.
    """

    def __init__(self, is_world_modeling: bool = False):
        self.controller_pbk = None  # type: Optional[str]

        self.search_id = 0
        self.search_ids_for_tac = set()  # type: Set[int]

        self._game_phase = GamePhase.PRE_GAME

        self._game_configuration = None  # type: Optional[GameConfiguration]
        self._initial_agent_state = None  # type: Optional[AgentState]
        self._agent_state = None  # type: Optional[AgentState]
        self._is_world_modeling = is_world_modeling
        self._world_state = None  # type: Optional[WorldState]

    def init(self, game_data: GameData):
        # populate data structures about the started competition
        self._game_configuration = GameConfiguration(game_data.nb_agents, game_data.nb_goods, game_data.tx_fee,
                                                     game_data.agent_pbks, game_data.agent_names, game_data.good_pbks)
        self._initial_agent_state = AgentState(game_data.money, game_data.endowment, game_data.utility_params)
        self._agent_state = AgentState(game_data.money, game_data.endowment, game_data.utility_params)
        if self.is_world_modeling:
            opponent_pbks = self.game_configuration.agent_pbks
            opponent_pbks.remove(game_data.public_key)
            self._world_state = WorldState(opponent_pbks, self.game_configuration.good_pbks, self.initial_agent_state)

    def reset(self):
        self.controller_pbk = None
        self.search_id = 0
        self.search_ids_for_tac = set()
        self._game_phase = GamePhase.PRE_GAME
        self._game_configuration = None
        self._initial_agent_state = None
        self._agent_state = None
        self._world_state = None

    @property
    def game_phase(self):
        return self._game_phase

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

    def get_next_search_id(self) -> int:
        """
        Generates the next search id and stores it.

        :return: a search id
        """
        self.search_id += 1
        self.search_ids_for_tac.add(self.search_id)
        return self.search_id


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


class ProtocolInterface:

    @abstractmethod
    def check_message(self, msg: AgentMessage) -> bool:
        pass


class BehaviourInterface:

    @abstractmethod
    def dispatch_to_handler(self, msg: AgentMessage) -> Optional[Action]:
        pass


class Dialogue(ProtocolInterface, BehaviourInterface):

    def __init__(self, agent: 'TACParticipantAgent', dialogue_label: DialogueLabel):
        self.agent = agent
        self.dialogue_label = dialogue_label
        self.messages = []  # type: List[AgentMessage]


class Dialogues:

    def __init__(self):
        self.dialogues = {}  # type: Dict[DialogueLabel, Dialogue]

    def is_dialogue_registered(self, dialogue_label) -> bool:
        return dialogue_label in self.dialogues

    def get_dialogue(self, dialogue_label: DialogueLabel) -> Dialogue:
        return self.dialogues[dialogue_label]

    def register_dialogue(self, dialogue: Dialogue) -> None:
        self.dialogues[dialogue.dialogue_label] = dialogue


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


class OEFSearchInterface:
    """
    This interface contains the methods to maintain OEF search logic.
    """

    @abstractmethod
    def on_search_result(self, search_result: SearchResult):
        """Handle search results."""

    @abstractmethod
    def on_oef_error(self, oef_error: OEFErrorMessage):
        """Handle an OEF error message."""

    @abstractmethod
    def on_dialogue_error(self, dialogue_error: DialogueErrorMessage):
        """Handler a dialogue error message"""


class DialogueInterface:
    """
    This interface contains the methods to maintain a Dialogue with other agents.
    """

    @abstractmethod
    def on_new_dialogue(self, msg) -> Dialogue:
        """Given a new message, create a Dialogue object that specifies:
        - the protocol rules that messages must follow;
        - how the agent behaves in this dialogue.
        """


class ControllerActions(ControllerInterface):

    def __init__(self, crypto: Crypto, liveness: Liveness, game_instance: TACGameInstance, out_box: 'OutBox', name: str):
        self.crypto = crypto
        self.liveness = liveness
        self.game_instance = game_instance
        self.out_box = out_box
        self.name = name

    def on_dialogue_error(self, dialogue_error: DialogueErrorMessage):
        pass

    def on_start(self) -> None:
        pass

    def on_transaction_confirmed(self, tx_confirmation: TransactionConfirmation) -> None:
        pass

    def on_state_update(self, agent_state: StateUpdate) -> None:
        pass

    def on_cancelled(self) -> None:
        """
        Handle the cancellation of the competition from the TAC controller.

        :return: None
        """
        logger.debug("[{}]: Received cancellation from the controller.".format(self.name))
        self.liveness._is_stopped = True

    def on_tac_error(self, error: Error) -> None:
        pass


class ControllerHandler(ControllerActions):

    def __init__(self, crypto: Crypto, liveness: Liveness, game_instance: TACGameInstance, out_box: 'OutBox', name: str):
        super().__init__(crypto, liveness, game_instance, out_box, name)

    def handle_controller_message(self, msg: ControllerMessage) -> None:
        """
        Handles messages from the controller.

        The controller does not expect a response for any of these messages.

        :return: None
        """
        response = Response.from_pb(msg.msg, msg.destination, self.crypto)  # TODO this is already created once above!
        logger.debug("[{}]: Handling controller response. type={}".format(self.name, type(response)))
        try:
            if msg.destination != self.game_instance.controller_pbk:
                raise ValueError("The sender of the message is not a controller agent.")

            if isinstance(response, Error):
                self.on_tac_error(response)
            elif self.game_instance.game_phase == GamePhase.PRE_GAME:
                raise ValueError("We do not except a controller agent message in the pre game phase.")
            elif self.game_instance.game_phase == GamePhase.GAME_SETUP:
                if isinstance(response, GameData):
                    self.game_instance.init(response)
                    self.game_instance._game_phase = GamePhase.GAME
                    self.on_start()
                elif isinstance(response, Cancelled):
                    self.game_instance._game_phase = GamePhase.POST_GAME
                    self.on_cancelled()
            elif self.game_instance.game_phase == GamePhase.GAME:
                if isinstance(response, TransactionConfirmation):
                    self.on_transaction_confirmed(response)
                elif isinstance(response, Cancelled):
                    self.game_instance._game_phase = GamePhase.POST_GAME
                    self.on_cancelled()
                elif isinstance(response, StateUpdate):
                    self.on_state_update(response)
            elif self.game_instance.game_phase == GamePhase.POST_GAME:
                raise ValueError("We do not except a controller agent message in the post game phase.")
        except ValueError as e:
            logger.warning(str(e))


class OEFActions(OEFSearchInterface):

    def __init__(self, crypto: Crypto, liveness: Liveness, game_instance: TACGameInstance, out_box: 'OutBox', name: str):
        self.crypto = crypto
        self.liveness = liveness
        self.game_instance = game_instance
        self.out_box = out_box
        self.name = name

    def search_for_tac(self) -> None:
        """
        Search for active TAC Controller.

        We assume that the controller is registered as a service with the 'tac' data model
        and with an attribute version = 1.

        :return: None
        """
        query = Query([Constraint("version", GtEq(1))])
        search_id = self.game_instance.get_next_search_id()
        self.out_box.out_queue.put(OutContainer(query=query, search_id=search_id))

    def on_search_result(self, search_result: SearchResult):
        """Process a search result from the OEF."""
        search_id = search_result.msg_id
        if search_id in self.game_instance.search_ids_for_tac:
            if len(search_result.agents) == 0:
                logger.debug("[{}]: Couldn't find the TAC controller.".format(self.name))
                self.liveness._is_stopped = True
            elif len(search_result.agents) > 1:
                logger.debug("[{}]: Found more than one TAC controller.".format(self.name))
                self.liveness._is_stopped = True
            else:
                controller_pbk = search_result.agents[0]
                self._register_to_tac(controller_pbk)
        else:
            self._react_to_search_results(search_id, search_result.agents)

    def on_oef_error(self, oef_error: OEFErrorMessage) -> None:
        pass

    def on_dialogue_error(self, dialogue_error: DialogueErrorMessage):
        pass

    def _react_to_search_results(self, sender_id: str, agent_pbks: List[str]) -> None:
        pass

    def _register_to_tac(self, tac_controller_pbk: str) -> None:
        """
        Register to active TAC Controller.

        :param tac_controller_pbk: the public key of the controller.

        :return: None
        :raises AssertionError: if the agent is already registered.
        """
        self.game_instance.controller_pbk = tac_controller_pbk
        self.game_instance._game_phase = GamePhase.GAME_SETUP
        msg = Register(self.crypto.public_key, self.crypto, self.name).serialize()
        self.out_box.out_queue.put(OutContainer(msg=msg, msg_id=0, dialogue_id=0, destination=tac_controller_pbk))


class OEFHandler(OEFActions):

    def __init__(self, crypto: Crypto, liveness: Liveness, game_instance: TACGameInstance, out_box: 'OutBox', name: str):
        super().__init__(crypto, liveness, game_instance, out_box, name)

    def handle_oef_message(self, msg: OEFMessage) -> None:
        """
        Handles messages from the oef.

        The oef does not expect a response for any of these messages.

        :return: None
        """
        logger.debug("[{}]: Handling OEF message. type={}".format(self.name, type(msg)))
        if isinstance(msg, SearchResult):
            self.on_search_result(msg)
        elif isinstance(msg, OEFErrorMessage):
            self.on_oef_error(msg)
        elif isinstance(msg, DialogueErrorMessage):
            self.on_dialogue_error(msg)
        else:
            logger.warning("[{}]: OEF Message type not recognized.".format(self.name))


class DialogueActions(DialogueInterface):
    """
    Implements a basic dialogue interface.
    """

    def __init__(self, crypto: Crypto, liveness: Liveness, game_instance: TACGameInstance, out_box: OutBox, name: str):
        self.crypto = crypto
        self.liveness = liveness
        self.game_instance = game_instance
        self.out_box = out_box
        self.name = name

    def on_new_dialogue(self, msg) -> Dialogue:
        pass


class DialogueHandler(DialogueActions):
    """
    Handles the dialogue with another agent.
    """

    def __init__(self, crypto: Crypto, liveness: Liveness, game_instance: TACGameInstance, out_box: OutBox, name: str):
        super().__init__(crypto, liveness, game_instance, out_box, name)

        self.dialogues = Dialogues()

    def handle_dialogue_message(self, msg: AgentMessage) -> None:
        """
        Handles messages from the other agents.

        The agents expect a response.

        :return: None
        """
        logger.debug("Handling Dialogue message. type={}".format(type(msg)))
        dialogue_label = DialogueLabel(msg.dialogue_id, msg.destination)
        if self.dialogues.is_dialogue_registered(dialogue_label):
            dialogue = self.dialogues.get_dialogue(dialogue_label)
        else:
            dialogue = self.dialogues.new_dialogue(msg)

        if not dialogue.check_message(msg):
            self.out_box._mail_box.out_queue.put(DialogueErrorMessage)
        else:
            response = dialogue.dispatch_to_handler(msg)
            self.out_box._mail_box.out_queue.put(response)


class Agent:
    def __init__(self, name: str, oef_addr: str, oef_port: int = 10000):
        self._name = name
        self._crypto = Crypto()
        self._liveness = Liveness()

        self.mail_box = None  # type: MailBox
        self.in_box = None  # type: InBox
        self.out_box = None  # type: OutBox

    @property
    def name(self) -> str:
        return self._name

    @property
    def crypto(self) -> Crypto:
        return self._crypto

    @property
    def liveness(self) -> Liveness:
        return self._liveness

    def start(self) -> None:
        """
        Starts the mailbox.

        :return: None
        """
        self.mail_box.start()
        self.liveness._is_stopped = False
        self.run_main_loop()

    def run_main_loop(self) -> None:
        """
        Runs the main loop of the agent
        """
        logger.debug("[{}]: Start processing messages...".format(self.name))
        while not self.liveness.is_stopped:
            self.act()
            self.react()

    def stop(self) -> None:
        """
        Stops the mailbox.

        :return: None
        """
        logger.debug("[{}]: Stopping message processing...".format(self.name))
        self.liveness._is_stopped = True
        self.mail_box.stop()

    @abstractmethod
    def act(self) -> None:
        """
        Performs actions.

        :return: None
        """

    @abstractmethod
    def react(self) -> None:
        """
        Reacts to incoming events.

        :return: None
        """


class TACParticipantAgent(Agent):

    def __init__(self, name: str, oef_addr: str, oef_port: int = 10000, is_world_modeling: bool = False):
        super().__init__(name, oef_addr, oef_port)
        self.mail_box = FIPAMailBox(self.crypto.public_key, oef_addr, oef_port, loop=asyncio.get_event_loop())
        self.in_box = InBox(self.mail_box)
        self.out_box = OutBox(self.mail_box)

        self._is_competing = False  # type: bool
        self._game_instance = TACGameInstance(is_world_modeling)  # type: Optional[TACGameInstance]

        self.controller_handler = ControllerHandler(self.crypto, self.liveness, self.game_instance, self.out_box, self.name)
        self.oef_handler = OEFHandler(self.crypto, self.liveness, self.game_instance, self.out_box, self.name)
        self.dialogue_handler = DialogueHandler(self.crypto, self.liveness, self.game_instance, self.out_box, self.name)

    @property
    def game_instance(self) -> TACGameInstance:
        return self._game_instance

    @property
    def is_competing(self) -> bool:
        return self._is_competing

    def act(self) -> None:
        """
        Performs actions.

        :return: None
        """
        if not self.is_competing:
            self.oef_handler.search_for_tac()
            self._is_competing = True

    def react(self) -> None:
        """
        Reacts to incoming events. This is blocking.

        :return: None
        """
        self.out_box.send_nowait()

        msg = self.in_box.get_wait()  # type: Message

        if is_oef_message(msg):
            msg: OEFMessage
            self.oef_handler.handle_oef_message(msg)
        elif is_controller_message(msg, self.crypto):
            msg: ControllerMessage
            self.controller_handler.handle_controller_message(msg)
        else:
            msg: AgentMessage
            self.dialogue_handler.handle_dialogue_message(msg)

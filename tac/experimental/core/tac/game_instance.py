# -*- coding: utf-8 -*-

# ------------------------------------------------------------------------------
#
#   Copyright 2018-2019 Fetch.AI Limited
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------
from enum import Enum
from typing import Optional, Set

from tac.game import AgentState, WorldState, GameConfiguration
from tac.protocol import GameData


class GamePhase(Enum):
    PRE_GAME = 'pre_game'
    GAME_SETUP = 'game_setup'
    GAME = 'game'
    POST_GAME = 'post_game'


class GameInstance:
    """
    The GameInstance maintains state of the game from the agent's perspective.
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

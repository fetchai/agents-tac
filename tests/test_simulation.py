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

"""This module contains the tests of the simulation."""

import datetime
from threading import Thread
from typing import List

import numpy as np
import pytest

from tac.agents.controller.agent import ControllerAgent
from tac.agents.controller.base.states import Game
from tac.agents.controller.base.tac_parameters import TACParameters
from tac.agents.participant.base.strategy import SearchFor, RegisterAs
from tac.agents.participant.examples.baseline import BaselineAgent as BaselineAgentV1
from tac.agents.participant.examples.strategy import BaselineStrategy


def _init_baseline_agents(n: int, version: str, oef_addr: str, oef_port: int) -> List[BaselineAgentV1]:
    """Baseline agents initialization."""
    if version == "v1":
        return [BaselineAgentV1("baseline_{:02}".format(i), "127.0.0.1", 10000,
                                BaselineStrategy(search_for=SearchFor.BOTH, register_as=RegisterAs.BOTH),
                                pending_transaction_timeout=120) for i in range(n)]


def _run_baseline_agent(agent: BaselineAgentV1, version: str) -> None:
    """Run a baseline agent. The version."""
    if version == "v1":
        agent.start()
    else:
        pytest.fail("Baseline agent version not recognized: {} (must be 'v1')")


@pytest.fixture(params=["v1"])
def baseline_version(request):
    """Version setting."""
    return request.param


class TestSimulation:
    """Class to test the simulation."""

    @pytest.fixture(autouse=True)
    def _start_oef_node(self, network_node):
        pass

    @classmethod
    def setup_class(cls):
        """Class setup."""
        cls.baseline_agents = _init_baseline_agents(5, "v1", "127.0.0.1", 10000)

        cls.tac_parameters = TACParameters(min_nb_agents=5,
                                           money_endowment=200,
                                           nb_goods=5,
                                           tx_fee=1.0,
                                           base_good_endowment=2,
                                           lower_bound_factor=0,
                                           upper_bound_factor=0,
                                           start_time=datetime.datetime.now() + datetime.timedelta(0, 2),
                                           registration_timeout=8,
                                           competition_timeout=20,
                                           inactivity_timeout=15)

        cls.tac_controller = ControllerAgent('controller', '127.0.0.1', 10000, cls.tac_parameters)

        # run the simulation
        try:
            controller_thread = Thread(target=cls.tac_controller.start)

            baseline_threads = [Thread(target=_run_baseline_agent, args=[baseline_agent, "v1"])
                                for baseline_agent in cls.baseline_agents]

            # launch all thread.
            all_threads = [controller_thread] + baseline_threads
            for thread in all_threads:
                thread.start()

            # wait for every thread. This part is blocking.
            for thread in all_threads:
                thread.join()
        except Exception as e:
            pytest.fail("Got exception: {}".format(e))

    def test_nb_settled_transaction_greater_than_zero(self):
        """Test that at least one transaction has been confirmed."""
        assert len(self.tac_controller.game_handler.current_game.transactions) > 0

    def test_game_took_place(self):
        """Test that the game actually took place, as expected."""
        assert self.tac_controller.game_handler.current_game is not None

    def test_baseline_agent_score_does_not_decrease(self):
        """Test that all the baseline agent scores do not decrease after each transaction."""
        finished_game = self.tac_controller.game_handler.current_game
        game_configuration = finished_game.configuration
        game_initialization = finished_game.initialization
        game = Game(game_configuration, game_initialization)

        scores_dict = game.get_scores()
        current_score = np.asarray(list(scores_dict.values()))
        next_scores = None
        for tx in finished_game.transactions:
            game.settle_transaction(tx)
            scores_dict = game.get_scores()
            next_scores = np.asarray(list(scores_dict.values()))
            assert not (next_scores < current_score).any()
            current_score = next_scores

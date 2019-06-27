# -*- coding: utf-8 -*-
import asyncio
import datetime
from threading import Thread
from typing import Union, List

import numpy as np
import pytest

from tac.agents.v2.base.strategy import SearchFor, RegisterAs
from tac.agents.v2.examples.strategy import BaselineStrategy
from tac.platform.game import Game

from tac.agents.v1.examples.baseline import BaselineAgent as BaselineAgentV1
from tac.agents.v2.examples.baseline import BaselineAgent as BaselineAgentV2

from tac.platform.controller import ControllerAgent, TACParameters


def _init_baseline_agents(n: int, version: str, oef_addr: str, oef_port: int) -> Union[List[BaselineAgentV1], List[BaselineAgentV2]]:
    if version == "v1":
        return [BaselineAgentV1("baseline_{:02}".format(i), "127.0.0.1", 10000,
                                search_for='both', register_as='both', pending_transaction_timeout=120,
                                loop=asyncio.new_event_loop()) for i in range(n)]
    elif version == "v2":
        return [BaselineAgentV2("baseline_{:02}".format(i), "127.0.0.1", 10000,
                                BaselineStrategy(search_for=SearchFor.BOTH, register_as=RegisterAs.BOTH),
                                pending_transaction_timeout=120) for i in range(n)]


def _run_baseline_agent(agent: Union[BaselineAgentV1, BaselineAgentV2], version: str) -> None:
    """Run a baseline agent. The version."""
    if version == "v1":
        agent.connect()
        agent.search_for_tac()
        agent.run()
    elif version == "v2":
        agent.start()
    else:
        pytest.fail("Baseline agent version not recognized: {} (must be either 'v1' or 'v2')")


@pytest.fixture(params=["v1", "v2"])
def baseline_version(request):
    return request.param


class TestSimulation:

    @pytest.fixture(autouse=True)
    def _start_oef_node(self, network_node):
        pass

    @classmethod
    def setup_class(cls):
        cls.tac_controller = ControllerAgent(loop=asyncio.new_event_loop())
        cls.tac_controller.connect()
        cls.tac_controller.register()

        cls.baseline_agents = _init_baseline_agents(5, "v2", "127.0.0.1", 10000)

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
                                           inactivity_timeout=10)

        # run the simulation
        try:
            # generate task for the controller
            controller_thread = Thread(target=cls.tac_controller.start_competition, args=(cls.tac_parameters, ))

            baseline_threads = [Thread(target=_run_baseline_agent, args=[baseline_agent, "v2"])
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
        """
        Test that at least one transaction has been confirmed.
        """
        assert len(self.tac_controller.game_handler.current_game.transactions) > 0

    def test_game_took_place(self):
        """Test that the game actually took place, as expected."""
        assert self.tac_controller.game_handler.current_game is not None

    def test_baseline_agent_score_does_not_decrease(self):
        """
        Test that all the baseline agent scores do not decrease after each transaction.
        """

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

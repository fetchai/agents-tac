# -*- coding: utf-8 -*-
import asyncio
from threading import Thread

import numpy as np
import pytest
from tac.game import Game

from tac.agents.baseline import BaselineAgent

from tac.agents.controller import ControllerAgent, TACParameters


def _run_baseline_agent(agent: BaselineAgent) -> None:
    """Run a baseline agent."""
    agent.connect()
    agent.search_for_tac()
    agent.run()


class TestSimulation:

    @pytest.fixture(autouse=True)
    def _start_oef_node(self, network_node):
        pass

    @classmethod
    def setup_class(cls):
        cls.tac_controller = ControllerAgent(loop=asyncio.new_event_loop())
        cls.tac_controller.connect()
        cls.tac_controller.register()

        cls.baseline_agents = [BaselineAgent("baseline_{:02}".format(i), "127.0.0.1", 3333, loop=asyncio.new_event_loop()) for i in range(15)]

        cls.tac_parameters = TACParameters(min_nb_agents=15,
                                           money_endowment=200,
                                           nb_goods=10,
                                           tx_fee=2.0,
                                           base_good_endowment=2,
                                           lower_bound_factor=0,
                                           upper_bound_factor=0,
                                           start_time=None,
                                           registration_timeout=5,
                                           competition_timeout=25,
                                           inactivity_timeout=10)

        # run the simulation
        try:
            # generate task for the controller
            controller_thread = Thread(target=cls.tac_controller.start_competition, args=(cls.tac_parameters, ))

            baseline_threads = [Thread(target=_run_baseline_agent, args=[baseline_agent]) for baseline_agent in cls.baseline_agents]

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

    def test_baseline_agent_score_does_not_decrease(self):
        """
        Test that all the baseline agent scores do not decrease after each transaction.
        """

        finished_game = self.tac_controller.game_handler.current_game
        game_configuration = finished_game.configuration
        game_initialization = finished_game.initialization
        game = Game(game_configuration, game_initialization)

        current_score = np.asarray(game.get_scores())
        next_scores = None
        for tx in finished_game.transactions:
            game.settle_transaction(tx)
            next_scores = np.asarray(game.get_scores())
            assert not (next_scores < current_score).any()
            current_score = next_scores



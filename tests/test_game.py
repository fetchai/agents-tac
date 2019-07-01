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

"""This module contains the tests of the game module."""

import pytest

from tac.platform.game import GameConfiguration, GameInitialization, Game, GameTransaction, AgentState, GoodState


class TestGameConfiguration:
    """Class to test the game configuration class."""

    def test_not_enough_agents_raises_exception(self):
        """Test that if we try to instantiate a game_configuration with not enough agents, we raise an AssertionError."""
        with pytest.raises(AssertionError, match="Must have at least two agents."):
            GameConfiguration(
                1,
                2,
                1.0,
                {'tac_agent_0_pbk': 'tac_agent_0'},
                {'tac_good_0': 'Good 0', 'tac_good_1': 'Good 1'}
            )

    def test_not_enough_goods_raises_exception(self):
        """Test that if we try to instantiate a game_configuration with not enough goods, we raise an AssertionError."""
        with pytest.raises(AssertionError, match="Must have at least two goods."):
            GameConfiguration(
                2,
                1,
                1.0,
                {'tac_agent_0_pbk': 'tac_agent_0', 'tac_agent_1_pbk': 'tac_agent_1'},
                {'tac_good_0': 'Good 0'}
            )

    def test_negative_tx_fee_raises_exception(self):
        """Test that if we try to instantiate a game_configuration with a negative tx_fee, we raise an AssertionError."""
        with pytest.raises(AssertionError, match="Tx fee must be non-negative."):
            GameConfiguration(
                2,
                2,
                - 1.0,
                {'tac_agent_0_pbk': 'tac_agent_0', 'tac_agent_1_pbk': 'tac_agent_1'},
                {'tac_good_0': 'Good 0', 'tac_good_1': 'Good 1'}
            )

    def test_non_unique_agent_names_raises_exception(self):
        """Test that if we try to instantiate a game_configuration with non unique agent names, we raise an AssertionError."""
        with pytest.raises(AssertionError, match="Agents' names must be unique."):
            GameConfiguration(
                2,
                2,
                1.0,
                {'tac_agent_0_pbk': 'tac_agent_0', 'tac_agent_1_pbk': 'tac_agent_0'},
                {'tac_good_0': 'Good 0', 'tac_good_1': 'Good 1'}
            )

    def test_agent_nb_and_public_keys_nonmatch_raises_exception(self):
        """Test that if we try to instantiate a game_configuration with a different number of agents from agent public keys, we raise an AssertionError."""
        with pytest.raises(AssertionError, match="There must be one public key for each agent."):
            GameConfiguration(
                3,
                2,
                1.0,
                {'tac_agent_0_pbk': 'tac_agent_0', 'tac_agent_1_pbk': 'tac_agent_1'},
                {'tac_good_0': 'Good 0', 'tac_good_1': 'Good 1'}
            )

    def test_non_unique_good_names_raises_exception(self):
        """Test that if we try to instantiate a game_configuration with non unique good names, we raise an AssertionError."""
        with pytest.raises(AssertionError, match="Goods' names must be unique."):
            GameConfiguration(
                2,
                2,
                1.0,
                {'tac_agent_0_pbk': 'tac_agent_0', 'tac_agent_1_pbk': 'tac_agent_1'},
                {'tac_good_0': 'Good 0', 'tac_good_1': 'Good 0'}
            )

    def test_good_nb_and_public_keys_nonmatch_raises_exception(self):
        """Test that if we try to instantiate a game_configuration with a different number of goods from good public keys, we raise an AssertionError."""
        with pytest.raises(AssertionError, match="There must be one public key for each good."):
            GameConfiguration(
                2,
                3,
                1.0,
                {'tac_agent_0_pbk': 'tac_agent_0', 'tac_agent_1_pbk': 'tac_agent_1'},
                {'tac_good_0': 'Good 0', 'tac_good_1': 'Good 1'}
            )

    def test_to_dict(self):
        """Test that conversion into dict works as expected."""
        nb_agents = 10
        nb_goods = 10
        tx_fee = 2.5
        agent_pbk_to_name = {'tac_agent_0_pbk': 'tac_agent_0', 'tac_agent_1_pbk': 'tac_agent_1', 'tac_agent_2_pbk': 'tac_agent_2', 'tac_agent_3_pbk': 'tac_agent_3', 'tac_agent_4_pbk': 'tac_agent_4', 'tac_agent_5_pbk': 'tac_agent_5', 'tac_agent_6_pbk': 'tac_agent_6', 'tac_agent_7_pbk': 'tac_agent_7', 'tac_agent_8_pbk': 'tac_agent_8', 'tac_agent_9_pbk': 'tac_agent_9'}
        good_pbk_to_name = {'tac_good_0_pbk': 'tac_good_0', 'tac_good_1_pbk': 'tac_good_1', 'tac_good_2_pbk': 'tac_good_2', 'tac_good_3_pbk': 'tac_good_3', 'tac_good_4_pbk': 'tac_good_4', 'tac_good_5_pbk': 'tac_good_5', 'tac_good_6_pbk': 'tac_good_6', 'tac_good_7_pbk': 'tac_good_7', 'tac_good_8_pbk': 'tac_good_8', 'tac_good_9_pbk': 'tac_good_9'}

        game_configuration = GameConfiguration(
            nb_agents,
            nb_goods,
            tx_fee,
            agent_pbk_to_name,
            good_pbk_to_name
        )

        actual_game_configuration_dict = game_configuration.to_dict()
        expected_game_configuration_dict = {
            "nb_agents": nb_agents,
            "nb_goods": nb_goods,
            "tx_fee": tx_fee,
            "agent_pbk_to_name": agent_pbk_to_name,
            "good_pbk_to_name": good_pbk_to_name
        }

        assert actual_game_configuration_dict == expected_game_configuration_dict

    def test_from_dict(self):
        """Test that conversion from dict works as expected."""
        nb_agents = 10
        nb_goods = 10
        tx_fee = 2.5
        agent_pbk_to_name = {'tac_agent_0_pbk': 'tac_agent_0', 'tac_agent_1_pbk': 'tac_agent_1', 'tac_agent_2_pbk': 'tac_agent_2', 'tac_agent_3_pbk': 'tac_agent_3', 'tac_agent_4_pbk': 'tac_agent_4', 'tac_agent_5_pbk': 'tac_agent_5', 'tac_agent_6_pbk': 'tac_agent_6', 'tac_agent_7_pbk': 'tac_agent_7', 'tac_agent_8_pbk': 'tac_agent_8', 'tac_agent_9_pbk': 'tac_agent_9'}
        good_pbk_to_name = {'tac_good_0_pbk': 'tac_good_0', 'tac_good_1_pbk': 'tac_good_1', 'tac_good_2_pbk': 'tac_good_2', 'tac_good_3_pbk': 'tac_good_3', 'tac_good_4_pbk': 'tac_good_4', 'tac_good_5_pbk': 'tac_good_5', 'tac_good_6_pbk': 'tac_good_6', 'tac_good_7_pbk': 'tac_good_7', 'tac_good_8_pbk': 'tac_good_8', 'tac_good_9_pbk': 'tac_good_9'}

        expected_game_configuration = GameConfiguration(nb_agents, nb_goods, tx_fee, agent_pbk_to_name, good_pbk_to_name)
        actual_game_configuration = GameConfiguration.from_dict(expected_game_configuration.to_dict())

        assert actual_game_configuration == expected_game_configuration


class TestGameIntitialization:
    """Class to test the game initialization class."""

    def test_negative_money_raises_exception(self):
        """Test that if we try to instantiate a game with a negative amount of money, we raise an AssertionError."""
        initial_money_amounts = [-20, 20, 20]
        endowments = [
            [1, 1, 4],
            [1, 5, 1],
            [6, 1, 2]
        ]
        utility_params = [
            [0.3, 0.4, 0.3],
            [0.1, 0.8, 0.1],
            [0.3, 0.2, 0.5]
        ]
        eq_prices = [1.0, 1.0, 4.0]
        eq_good_holdings = [
            [1.0, 1.0, 4.0],
            [1.0, 5.0, 1.0],
            [6.0, 1.0, 2.0]
        ]
        eq_money_holdings = [20.0, 20.0, 20.0]
        with pytest.raises(AssertionError, match="Money must be non-negative."):
            GameInitialization(
                initial_money_amounts,
                endowments,
                utility_params,
                eq_prices,
                eq_good_holdings,
                eq_money_holdings
            )

    def test_negative_endowments_raises_exception(self):
        """Test that if we try to instantiate a game with a negative amount of money, we raise an AssertionError."""
        initial_money_amounts = [20, 20, 20]
        endowments = [
            [-1, 1, 4],
            [1, 5, 1],
            [6, 1, 2]
        ]
        utility_params = [
            [0.3, 0.4, 0.3],
            [0.1, 0.8, 0.1],
            [0.3, 0.2, 0.5]
        ]
        eq_prices = [1.0, 1.0, 4.0]
        eq_good_holdings = [
            [1.0, 1.0, 4.0],
            [1.0, 5.0, 1.0],
            [6.0, 1.0, 2.0]
        ]
        eq_money_holdings = [20.0, 20.0, 20.0]
        with pytest.raises(AssertionError, match="Endowments must be strictly positive."):
            GameInitialization(
                initial_money_amounts,
                endowments,
                utility_params,
                eq_prices,
                eq_good_holdings,
                eq_money_holdings
            )

    def test_negative_utilities_raises_exception(self):
        """Test that if we try to instantiate a game with a negative utility, we raise an AssertionError."""
        initial_money_amounts = [20, 20, 20]
        endowments = [
            [1, 1, 4],
            [1, 5, 1],
            [6, 1, 2]
        ]
        utility_params = [
            [0.3, -0.4, 0.3],
            [0.1, 0.8, 0.1],
            [0.3, 0.2, 0.5]
        ]
        eq_prices = [1.0, 1.0, 4.0]
        eq_good_holdings = [
            [1.0, 1.0, 4.0],
            [1.0, 5.0, 1.0],
            [6.0, 1.0, 2.0]
        ]
        eq_money_holdings = [20.0, 20.0, 20.0]
        with pytest.raises(AssertionError, match="UtilityParams must be strictly positive."):
            GameInitialization(
                initial_money_amounts,
                endowments,
                utility_params,
                eq_prices,
                eq_good_holdings,
                eq_money_holdings
            )

    def test_to_dict(self):
        """Test that conversion into dict works as expected."""
        initial_money_amounts = [20, 20, 20]
        endowments = [
            [1, 1, 4],
            [1, 5, 1],
            [6, 1, 2]
        ]
        utility_params = [
            [0.3, 0.4, 0.3],
            [0.1, 0.8, 0.1],
            [0.3, 0.2, 0.5]
        ]
        eq_prices = [1.0, 1.0, 4.0]
        eq_good_holdings = [
            [1.0, 1.0, 4.0],
            [1.0, 5.0, 1.0],
            [6.0, 1.0, 2.0]
        ]
        eq_money_holdings = [20.0, 20.0, 20.0]

        game_initialization = GameInitialization(
            initial_money_amounts,
            endowments,
            utility_params,
            eq_prices,
            eq_good_holdings,
            eq_money_holdings
        )

        actual_game_initialization_dict = game_initialization.to_dict()
        expected_game_initialization_dict = {
            "initial_money_amounts": initial_money_amounts,
            "endowments": endowments,
            "utility_params": utility_params,
            "eq_prices": eq_prices,
            "eq_good_holdings": eq_good_holdings,
            "eq_money_holdings": eq_money_holdings
        }

        assert actual_game_initialization_dict == expected_game_initialization_dict

    def test_from_dict(self):
        """Test that conversion from dict works as expected."""
        initial_money_amounts = [20, 20, 20]
        endowments = [
            [1, 1, 4],
            [1, 5, 1],
            [6, 1, 2]
        ]
        utility_params = [
            [0.3, 0.4, 0.3],
            [0.1, 0.8, 0.1],
            [0.3, 0.2, 0.5]
        ]
        eq_prices = [1.0, 1.0, 4.0]
        eq_good_holdings = [
            [1.0, 1.0, 4.0],
            [1.0, 5.0, 1.0],
            [6.0, 1.0, 2.0]
        ]
        eq_money_holdings = [20.0, 20.0, 20.0]

        expected_game_initialization = GameInitialization(
            initial_money_amounts,
            endowments,
            utility_params,
            eq_prices,
            eq_good_holdings,
            eq_money_holdings
        )
        actual_game_initialization = GameInitialization.from_dict(expected_game_initialization.to_dict())

        assert actual_game_initialization == expected_game_initialization


class TestGame:
    """Class to test the game class."""

    def test_transaction_invalid_if_buyer_does_not_have_enough_money(self):
        """Test that a transaction is invalid if the buyer does not have enough money."""
        nb_agents = 3
        nb_goods = 3
        tx_fee = 1.0
        agent_pbk_to_name = {'tac_agent_0_pbk': 'tac_agent_0', 'tac_agent_1_pbk': 'tac_agent_1', 'tac_agent_2_pbk': 'tac_agent_2'}
        good_pbk_to_name = {'tac_good_0_pbk': 'tac_good_0', 'tac_good_1_pbk': 'tac_good_1', 'tac_good_2_pbk': 'tac_good_2'}
        money_amounts = [20, 20, 20]
        endowments = [
            [1, 1, 1],
            [2, 1, 1],
            [1, 1, 2]
        ]
        utility_params = [
            [20.0, 40.0, 40.0],
            [10.0, 50.0, 40.0],
            [40.0, 30.0, 30.0]
        ]
        eq_prices = [1.0, 1.0, 4.0]
        eq_good_holdings = [
            [1.0, 1.0, 4.0],
            [1.0, 5.0, 1.0],
            [6.0, 1.0, 2.0]
        ]
        eq_money_holdings = [20.0, 20.0, 20.0]

        game_configuration = GameConfiguration(
            nb_agents,
            nb_goods,
            tx_fee,
            agent_pbk_to_name,
            good_pbk_to_name
        )
        game_initialization = GameInitialization(
            money_amounts,
            endowments,
            utility_params,
            eq_prices,
            eq_good_holdings,
            eq_money_holdings
        )

        game = Game(game_configuration, game_initialization)

        # not enough money: amount + fee > balance of player 0
        buyer_id = 'tac_agent_0_pbk'
        seller_id = 'tac_agent_1_pbk'
        amount = 20
        quantities_by_good = {0: 1, 1: 1, 2: 1}
        invalid_transaction = GameTransaction(buyer_id, seller_id, amount, quantities_by_good)

        # transaction is invalide because buyer_balance < amount + fee
        assert not game.is_transaction_valid(invalid_transaction)

    def test_transaction_invalid_if_seller_does_not_have_enough_quantities(self):
        """Test that a transaction is invalid if the seller does not have enough quantities."""
        nb_agents = 3
        nb_goods = 3
        tx_fee = 1.0
        agent_pbk_to_name = {'tac_agent_0_pbk': 'tac_agent_0', 'tac_agent_1_pbk': 'tac_agent_1', 'tac_agent_2_pbk': 'tac_agent_2'}
        good_pbk_to_name = {'tac_good_0_pbk': 'tac_good_0', 'tac_good_1_pbk': 'tac_good_1', 'tac_good_2_pbk': 'tac_good_2'}
        money_amounts = [20, 20, 20]
        endowments = [
            [1, 1, 1],
            [2, 1, 1],
            [1, 1, 2]
        ]
        utility_params = [
            [20.0, 40.0, 40.0],
            [10.0, 50.0, 40.0],
            [40.0, 30.0, 30.0]
        ]
        eq_prices = [1.0, 1.0, 4.0]
        eq_good_holdings = [
            [1.0, 1.0, 4.0],
            [1.0, 5.0, 1.0],
            [6.0, 1.0, 2.0]
        ]
        eq_money_holdings = [20.0, 20.0, 20.0]

        game_configuration = GameConfiguration(
            nb_agents,
            nb_goods,
            tx_fee,
            agent_pbk_to_name,
            good_pbk_to_name
        )
        game_initialization = GameInitialization(
            money_amounts,
            endowments,
            utility_params,
            eq_prices,
            eq_good_holdings,
            eq_money_holdings
        )

        game = Game(game_configuration, game_initialization)

        buyer_id = 'tac_agent_0_pbk'
        seller_id = 'tac_agent_1_pbk'
        amount = 20
        quantities_by_good = {0: 3, 1: 0, 2: 0}
        invalid_transaction = GameTransaction(buyer_id, seller_id, amount, quantities_by_good)

        assert not game.is_transaction_valid(invalid_transaction)

    def test_generate_game(self):
        """Test the game generation algorithm."""
        nb_agents = 3
        nb_goods = 3
        money_endowment = 20
        tx_fee = 2.5
        base_amount = 2
        lower_bound_factor = 1
        upper_bound_factor = 3
        agent_pbk_to_name = {'tac_agent_0_pbk': 'tac_agent_0', 'tac_agent_1_pbk': 'tac_agent_1', 'tac_agent_2_pbk': 'tac_agent_2'}
        good_pbk_to_name = {'tac_good_0_pbk': 'tac_good_0', 'tac_good_1_pbk': 'tac_good_1', 'tac_good_2_pbk': 'tac_good_2'}

        _ = Game.generate_game(nb_agents, nb_goods, money_endowment, tx_fee, base_amount, lower_bound_factor, upper_bound_factor, agent_pbk_to_name, good_pbk_to_name)

        # please look at the assertions in tac.game.GameConfiguration._check_consistency()

    def test_get_game_data_from_agent_label(self):
        """Test that the getter of game states by agent label works as expected."""
        nb_agents = 3
        nb_goods = 3
        tx_fee = 1.0
        agent_pbk_to_name = {'tac_agent_0_pbk': 'tac_agent_0', 'tac_agent_1_pbk': 'tac_agent_1', 'tac_agent_2_pbk': 'tac_agent_2'}
        good_pbk_to_name = {'tac_good_0_pbk': 'tac_good_0', 'tac_good_1_pbk': 'tac_good_1', 'tac_good_2_pbk': 'tac_good_2'}
        money_amounts = [20, 20, 20]
        endowments = [
            [1, 1, 1],
            [2, 1, 1],
            [1, 1, 2]
        ]
        utility_params = [
            [20.0, 40.0, 40.0],
            [10.0, 50.0, 40.0],
            [40.0, 30.0, 30.0]
        ]
        eq_prices = [1.0, 1.0, 4.0]
        eq_good_holdings = [
            [1.0, 1.0, 4.0],
            [1.0, 5.0, 1.0],
            [6.0, 1.0, 2.0]
        ]
        eq_money_holdings = [20.0, 20.0, 20.0]

        game_configuration = GameConfiguration(
            nb_agents,
            nb_goods,
            tx_fee,
            agent_pbk_to_name,
            good_pbk_to_name
        )
        game_initialization = GameInitialization(
            money_amounts,
            endowments,
            utility_params,
            eq_prices,
            eq_good_holdings,
            eq_money_holdings
        )

        game = Game(game_configuration, game_initialization)

        actual_agent_state_0 = game.get_agent_state_from_agent_pbk("tac_agent_0_pbk")
        actual_agent_state_1 = game.get_agent_state_from_agent_pbk("tac_agent_1_pbk")

        expected_agent_state_0 = AgentState(money_amounts[0], endowments[0], utility_params[0])
        expected_agent_state_1 = AgentState(money_amounts[1], endowments[1], utility_params[1])

        assert actual_agent_state_0 == expected_agent_state_0
        assert actual_agent_state_1 == expected_agent_state_1

    def test_to_dict(self):
        """Test that conversion into dict works as expected."""
        nb_agents = 3
        nb_goods = 3
        tx_fee = 1.0
        agent_pbk_to_name = {'tac_agent_0_pbk': 'tac_agent_0', 'tac_agent_1_pbk': 'tac_agent_1', 'tac_agent_2_pbk': 'tac_agent_2'}
        good_pbk_to_name = {'tac_good_0_pbk': 'tac_good_0', 'tac_good_1_pbk': 'tac_good_1', 'tac_good_2_pbk': 'tac_good_2'}
        money_amounts = [20, 20, 20]
        endowments = [
            [1, 1, 1],
            [2, 1, 1],
            [1, 1, 2]
        ]
        utility_params = [
            [20.0, 40.0, 40.0],
            [10.0, 50.0, 40.0],
            [40.0, 30.0, 30.0]
        ]
        eq_prices = [1.0, 1.0, 4.0]
        eq_good_holdings = [
            [1.0, 1.0, 4.0],
            [1.0, 5.0, 1.0],
            [6.0, 1.0, 2.0]
        ]
        eq_money_holdings = [20.0, 20.0, 20.0]

        game_configuration = GameConfiguration(
            nb_agents,
            nb_goods,
            tx_fee,
            agent_pbk_to_name,
            good_pbk_to_name
        )
        game_initialization = GameInitialization(
            money_amounts,
            endowments,
            utility_params,
            eq_prices,
            eq_good_holdings,
            eq_money_holdings
        )

        game = Game(game_configuration, game_initialization)

        game_transaction_1 = GameTransaction('tac_agent_0_pbk', 'tac_agent_1_pbk', 10, {'tac_good_0_pbk': 1})
        game_transaction_2 = GameTransaction('tac_agent_1_pbk', 'tac_agent_0_pbk', 10, {'tac_good_0_pbk': 1})
        game.settle_transaction(game_transaction_1)
        game.settle_transaction(game_transaction_2)

        actual_game_dict = game.to_dict()
        expected_game_dict = {
            "configuration": game_configuration.to_dict(),
            "initialization": game_initialization.to_dict(),
            "transactions": [
                game_transaction_1.to_dict(),
                game_transaction_2.to_dict()
            ]
        }

        assert actual_game_dict == expected_game_dict

    def test_from_dict(self):
        """Test that conversion from dict works as expected."""
        nb_agents = 3
        nb_goods = 3
        tx_fee = 1.0
        agent_pbk_to_name = {'tac_agent_0_pbk': 'tac_agent_0', 'tac_agent_1_pbk': 'tac_agent_1', 'tac_agent_2_pbk': 'tac_agent_2'}
        good_pbk_to_name = {'tac_good_0_pbk': 'tac_good_0', 'tac_good_1_pbk': 'tac_good_1', 'tac_good_2_pbk': 'tac_good_2'}
        money_amounts = [20, 20, 20]
        endowments = [
            [1, 1, 1],
            [2, 1, 1],
            [1, 1, 2]
        ]
        utility_params = [
            [20.0, 40.0, 40.0],
            [10.0, 50.0, 40.0],
            [40.0, 30.0, 30.0]
        ]
        eq_prices = [1.0, 1.0, 4.0]
        eq_good_holdings = [
            [1.0, 1.0, 4.0],
            [1.0, 5.0, 1.0],
            [6.0, 1.0, 2.0]
        ]
        eq_money_holdings = [20.0, 20.0, 20.0]

        game_configuration = GameConfiguration(
            nb_agents,
            nb_goods,
            tx_fee,
            agent_pbk_to_name,
            good_pbk_to_name
        )
        game_initialization = GameInitialization(
            money_amounts,
            endowments,
            utility_params,
            eq_prices,
            eq_good_holdings,
            eq_money_holdings
        )

        expected_game = Game(game_configuration, game_initialization)

        game_transaction_1 = GameTransaction('tac_agent_0_pbk', 'tac_agent_1_pbk', 10, {'tac_good_0_pbk': 1})
        game_transaction_2 = GameTransaction('tac_agent_1_pbk', 'tac_agent_0_pbk', 10, {'tac_good_0_pbk': 1})
        expected_game.settle_transaction(game_transaction_1)
        expected_game.settle_transaction(game_transaction_2)

        actual_game = Game.from_dict(expected_game.to_dict())

        assert actual_game == expected_game


class TestGoodState:
    """Class to test the good state class."""

    def test_negative_price_raises_exception(self):
        """Test that if we try to instantiate a good_state with a negative price, we raise an AssertionError."""
        with pytest.raises(AssertionError, match="The price must be non-negative."):
            GoodState(
                -1
            )

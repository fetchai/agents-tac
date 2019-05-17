# -*- coding: utf-8 -*-
import pytest

from tac.game import GameConfiguration, GameInitialization, Game, GameTransaction, AgentState, GoodState


class TestGameConfiguration:

    def test_not_enough_agents_raises_exception(self):
        """Test that if we try to instantiate a game_configuration with not enough agents, we raise an AssertionError."""
        with pytest.raises(AssertionError, match="Must have at least two agents."):
            GameConfiguration(
                1,
                2,
                1.0,
                ['tac_agent_0'],
                ['tac_good_0', 'tac_good_1']
            )

    def test_not_eenough_goods_raises_exception(self):
        """Test that if we try to instantiate a game_configuration with not enough goods, we raise an AssertionError."""
        with pytest.raises(AssertionError, match="Must have at least two goods."):
            GameConfiguration(
                2,
                1,
                1.0,
                ['tac_agent_0', 'tac_agent_1'],
                ['tac_good_0']
            )

    def test_negative_tx_fee_raises_exception(self):
        """Test that if we try to instantiate a game_configuration with a negative tx_fee, we raise an AssertionError."""
        with pytest.raises(AssertionError, match="Tx fee must be non-negative."):
            GameConfiguration(
                2,
                2,
                - 1.0,
                ['tac_agent_0', 'tac_agent_1'],
                ['tac_good_0', 'tac_good_1']
            )

    def test_non_unique_agent_pbks_raises_exception(self):
        """Test that if we try to instantiate a game_configuration with non unique agent pbks, we raise an AssertionError."""
        with pytest.raises(AssertionError, match="Agents' pbks must be unique."):
            GameConfiguration(
                2,
                2,
                1.0,
                ['tac_agent_0', 'tac_agent_0'],
                ['tac_good_0', 'tac_good_1']
            )

    def test_non_unique_good_pbks_raises_exception(self):
        """Test that if we try to instantiate a game_configuration with non unique good pbks, we raise an AssertionError."""
        with pytest.raises(AssertionError, match="Goods' pbks must be unique."):
            GameConfiguration(
                2,
                2,
                1.0,
                ['tac_agent_0', 'tac_agent_1'],
                ['tac_good_0', 'tac_good_0']
            )

    def test_to_dict(self):
        """Test that conversion into dict works as expected."""
        nb_agents = 10
        nb_goods = 10
        tx_fee = 2.5
        agent_pbks = ['tac_agent_0', 'tac_agent_1', 'tac_agent_2', 'tac_agent_3', 'tac_agent_4', 'tac_agent_5', 'tac_agent_6', 'tac_agent_7', 'tac_agent_8', 'tac_agent_9']
        good_pbks = ['tac_good_0', 'tac_good_1', 'tac_good_2', 'tac_good_3', 'tac_good_4', 'tac_good_5', 'tac_good_6', 'tac_good_7', 'tac_good_8', 'tac_good_9']

        game_configuration = GameConfiguration(
            nb_agents,
            nb_goods,
            tx_fee,
            agent_pbks,
            good_pbks
        )

        actual_game_configuration_dict = game_configuration.to_dict()
        expected_game_configuration_dict = {
            "nb_agents": nb_agents,
            "nb_goods": nb_goods,
            "tx_fee": tx_fee,
            "agent_pbks": agent_pbks,
            "good_pbks": good_pbks
        }

        assert actual_game_configuration_dict == expected_game_configuration_dict

    def test_from_dict(self):
        """Test that conversion from dict works as expected."""
        nb_agents = 10
        nb_goods = 10
        tx_fee = 2.5
        agent_pbks = ['tac_agent_0', 'tac_agent_1', 'tac_agent_2', 'tac_agent_3', 'tac_agent_4', 'tac_agent_5', 'tac_agent_6', 'tac_agent_7', 'tac_agent_8', 'tac_agent_9']
        good_pbks = ['tac_good_0', 'tac_good_1', 'tac_good_2', 'tac_good_3', 'tac_good_4', 'tac_good_5', 'tac_good_6', 'tac_good_7', 'tac_good_8', 'tac_good_9']

        expected_game_configuration = GameConfiguration(nb_agents, nb_goods, tx_fee, agent_pbks, good_pbks)
        actual_game_configuration = GameConfiguration.from_dict(expected_game_configuration.to_dict())

        assert actual_game_configuration == expected_game_configuration


class TestGameIntitialization:

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
        with pytest.raises(AssertionError, match="Money must be non-negative."):
            GameInitialization(
                initial_money_amounts,
                endowments,
                utility_params
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
        with pytest.raises(AssertionError, match="Endowments must be strictly positive."):
            GameInitialization(
                initial_money_amounts,
                endowments,
                utility_params
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
        with pytest.raises(AssertionError, match="UtilityParams must be strictly positive."):
            GameInitialization(
                initial_money_amounts,
                endowments,
                utility_params
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

        game_initialization = GameInitialization(
            initial_money_amounts,
            endowments,
            utility_params
        )

        actual_game_initialization_dict = game_initialization.to_dict()
        expected_game_initialization_dict = {
            "initial_money_amounts": initial_money_amounts,
            "endowments": endowments,
            "utility_params": utility_params
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

        expected_game_initialization = GameInitialization(
            initial_money_amounts,
            endowments,
            utility_params
        )
        actual_game_initialization = GameInitialization.from_dict(expected_game_initialization.to_dict())

        assert actual_game_initialization == expected_game_initialization


class TestGame:

    def test_transaction_invalid_if_buyer_does_not_have_enough_money(self):
        """Test that a transaction is invalid if the buyer does not have enough money."""

        nb_agents = 3
        nb_goods = 3
        tx_fee = 1.0
        agent_pbks = ['tac_agent_0', 'tac_agent_1', 'tac_agent_2']
        good_pbks = ['tac_good_0', 'tac_good_1', 'tac_good_2']
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
        game_configuration = GameConfiguration(
            nb_agents,
            nb_goods,
            tx_fee,
            agent_pbks,
            good_pbks,
        )
        game_initialization = GameInitialization(
            money_amounts,
            endowments,
            utility_params
        )

        game = Game(game_configuration, game_initialization)

        # not enough money: amount + fee > balance of player 0
        buyer_id = 'tac_agent_0'
        seller_id = 'tac_agent_1'
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
        agent_pbks = ['tac_agent_0', 'tac_agent_1', 'tac_agent_2']
        good_pbks = ['tac_good_0', 'tac_good_1', 'tac_good_2']
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
        game_configuration = GameConfiguration(
            nb_agents,
            nb_goods,
            tx_fee,
            agent_pbks,
            good_pbks,
        )
        game_initialization = GameInitialization(
            money_amounts,
            endowments,
            utility_params
        )

        game = Game(game_configuration, game_initialization)

        buyer_id = 'tac_agent_0'
        seller_id = 'tac_agent_1'
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
        lower_bound_factor = 1
        upper_bound_factor = 3
        agent_pbks = ['tac_agent_0', 'tac_agent_1', 'tac_agent_2']
        good_pbks = ['tac_good_0', 'tac_good_1', 'tac_good_2']

        _ = Game.generate_game(nb_agents, nb_goods, money_endowment, tx_fee, lower_bound_factor, upper_bound_factor, agent_pbks, good_pbks)

        # please look at the assertions in tac.game.GameConfiguration._check_consistency()

    def test_get_game_data_from_agent_label(self):
        """Test that the getter of game states by agent label works as expected."""

        nb_agents = 3
        nb_goods = 3
        tx_fee = 1.0
        agent_pbks = ['tac_agent_0', 'tac_agent_1', 'tac_agent_2']
        good_pbks = ['tac_good_0', 'tac_good_1', 'tac_good_2']
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
        game_configuration = GameConfiguration(
            nb_agents,
            nb_goods,
            tx_fee,
            agent_pbks,
            good_pbks,
        )
        game_initialization = GameInitialization(
            money_amounts,
            endowments,
            utility_params
        )

        game = Game(game_configuration, game_initialization)

        actual_agent_state_0 = game.get_agent_state_from_agent_pbk("tac_agent_0")
        actual_agent_state_1 = game.get_agent_state_from_agent_pbk("tac_agent_1")

        expected_agent_state_0 = AgentState(money_amounts[0], endowments[0], utility_params[0])
        expected_agent_state_1 = AgentState(money_amounts[1], endowments[1], utility_params[1])

        assert actual_agent_state_0 == expected_agent_state_0
        assert actual_agent_state_1 == expected_agent_state_1

    def test_to_dict(self):
        """Test that conversion into dict works as expected."""

        nb_agents = 3
        nb_goods = 3
        tx_fee = 1.0
        agent_pbks = ['tac_agent_0', 'tac_agent_1', 'tac_agent_2']
        good_pbks = ['tac_good_0', 'tac_good_1', 'tac_good_2']
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
        game_configuration = GameConfiguration(
            nb_agents,
            nb_goods,
            tx_fee,
            agent_pbks,
            good_pbks,
        )
        game_initialization = GameInitialization(
            money_amounts,
            endowments,
            utility_params
        )

        game = Game(game_configuration, game_initialization)

        game_transaction_1 = GameTransaction('tac_agent_0', 'tac_agent_1', 10, {'tac_good_0': 1})
        game_transaction_2 = GameTransaction('tac_agent_1', 'tac_agent_0', 10, {'tac_good_0': 1})
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
        agent_pbks = ['tac_agent_0', 'tac_agent_1', 'tac_agent_2']
        good_pbks = ['tac_good_0', 'tac_good_1', 'tac_good_2']
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
        game_configuration = GameConfiguration(
            nb_agents,
            nb_goods,
            tx_fee,
            agent_pbks,
            good_pbks,
        )
        game_initialization = GameInitialization(
            money_amounts,
            endowments,
            utility_params
        )

        expected_game = Game(game_configuration, game_initialization)

        game_transaction_1 = GameTransaction('tac_agent_0', 'tac_agent_1', 10, {'tac_good_0': 1})
        game_transaction_2 = GameTransaction('tac_agent_1', 'tac_agent_0', 10, {'tac_good_0': 1})
        expected_game.settle_transaction(game_transaction_1)
        expected_game.settle_transaction(game_transaction_2)

        actual_game = Game.from_dict(expected_game.to_dict())

        assert actual_game == expected_game


class TestGoodState:

    def test_negative_price_raises_exception(self):
        """Test that if we try to instantiate a good_state with a negative price, we raise an AssertionError."""
        with pytest.raises(AssertionError, match="The price must be non-negative."):
            GoodState(
                -1
            )

# -*- coding: utf-8 -*-
from typing import List, Set

import pytest

from tac.game import GameConfiguration, Game, GameTransaction, GameState


class TestGameConfiguration:

    def test_default_labels(self):
        """Test that default labels are created correctly (three agents)."""

        money_amounts = [20, 20, 20]
        endowments = [
            [1, 1, 0],
            [1, 0, 0],
            [0, 1, 2]
        ]
        utilities = [
            [20, 40, 60],
            [20, 60, 40],
            [40, 20, 60]
        ]
        fee = 1

        game_configuration = GameConfiguration(
            money_amounts,
            endowments,
            utilities,
            fee
        )

        assert len(game_configuration.agent_labels) == 3
        assert game_configuration.agent_labels[0] == "agent_00"
        assert game_configuration.agent_labels[1] == "agent_01"
        assert game_configuration.agent_labels[2] == "agent_02"

    def test_get_label_from_id(self):
        """Test that the association between labels and agent ids works correctly."""
        money_amounts = [20, 20]
        endowments = [
            [0, 1],
            [1, 0]
        ]
        utilities = [
            [20, 40],
            [40, 20]
        ]
        fee = 1

        game_configuration = GameConfiguration(money_amounts, endowments, utilities, fee, ["agent_01", "agent_02"])

        assert game_configuration.agent_id_from_label("agent_01") == 0
        assert game_configuration.agent_id_from_label("agent_02") == 1

    def test_create_game_states(self):
        """Test that the game states for every player are created as expected."""
        money_amounts = [20, 20]
        endowments = [
            [0, 1],
            [1, 0]
        ]
        utilities = [
            [20, 40],
            [40, 20]
        ]
        fee = 1
        game_configuration = GameConfiguration(money_amounts, endowments, utilities, fee, ["agent_01", "agent_02"])

        actual_game_states = game_configuration.create_game_states()

        actual_game_state_0 = actual_game_states[0]
        actual_game_state_1 = actual_game_states[1]

        expected_game_state_0 = GameState(20, [0, 1], [20, 40])
        expected_game_state_1 = GameState(20, [1, 0], [40, 20])

        assert actual_game_state_0 == expected_game_state_0
        assert actual_game_state_1 == expected_game_state_1

    def test_negative_money_raises_exception(self):
        """Test that if we try to instantiate a game with a negative amount of money, we raise an AssertionError."""
        with pytest.raises(AssertionError, match="All the money must be a non-negative value"):
            game_configuration = GameConfiguration(
                [20, -20],
                [
                    [1, 1],
                    [1, 1]
                ],
                [
                    [20, 40],
                    [20, 40]
                ],
                1
            )

    def test_negative_endowments_raises_exception(self):
        """Test that if we try to instantiate a game with a negative amount of money, we raise an AssertionError."""
        with pytest.raises(AssertionError, match="Endowments must be non-negative."):
            game_configuration = GameConfiguration(
                [20, 20],
                [
                    [1, 1],
                    [1, -1]
                ],
                [
                    [20, 40],
                    [20, 40]
                ],
                1
            )

    def test_negative_utilities_raises_exception(self):
        """Test that if we try to instantiate a game with a negative utility, we raise an AssertionError."""
        with pytest.raises(AssertionError, match="Utilities must be non-negative."):
            game_configuration = GameConfiguration(
                [20, 20],
                [
                    [1, 1],
                    [1, 1]
                ],
                [
                    [20, -40],
                    [20, -40]
                ],
                1
            )

    def test_negative_fee_raises_exception(self):
        """Test that if we try to instantiate a game with a negative fee value, we raise an AssertionError."""
        with pytest.raises(AssertionError, match="Fee must be non-negative."):
            game_configuration = GameConfiguration(
                [20, 20],
                [
                    [1, 1],
                    [1, 1]
                ],
                [
                    [20, 40],
                    [20, 40]
                ],
                -1
            )

    def test_to_dict(self):
        """Test that conversion into dict works as expected."""
        money_amounts = [20, 20, 20]
        endowments = [
            [1, 1, 0],
            [1, 0, 0],
            [0, 1, 2]
        ]
        utilities = [
            [20, 40, 60],
            [20, 60, 40],
            [40, 20, 60]
        ]
        fee = 1
        agent_labels = ["agent_01", "agent_02", "agent_03"]

        game_configuration = GameConfiguration(
            money_amounts,
            endowments,
            utilities,
            fee,
            agent_labels=agent_labels
        )

        actual_game_configuration_dict = game_configuration.to_dict()
        expected_game_configuration_dict = {
            "initial_money_amounts": money_amounts,
            "endowments": endowments,
            "utilities": utilities,
            "fee": fee,
            "agent_labels": agent_labels
        }

        assert actual_game_configuration_dict == expected_game_configuration_dict

    def test_from_dict(self):
        """Test that conversion from dict works as expected."""
        money_amounts = [20, 20, 20]
        endowments = [
            [1, 1, 0],
            [1, 0, 0],
            [0, 1, 2]
        ]
        utilities = [
            [20, 40, 60],
            [20, 60, 40],
            [40, 20, 60]
        ]
        fee = 1
        agent_labels = ["agent_01", "agent_02", "agent_03"]

        expected_game_configuration = GameConfiguration(money_amounts, endowments, utilities, fee, agent_labels)
        actual_game_configuration = GameConfiguration.from_dict(expected_game_configuration.to_dict())

        assert actual_game_configuration == expected_game_configuration


class TestGame:

    def test_transaction_invalid_if_buyer_does_not_have_enough_money(self):
        """Test that a transaction is invalid if the buyer does not have enough money."""

        money_amounts = [20, 20, 20]
        endowments = [
            [1, 1, 0],
            [1, 0, 0],
            [0, 1, 2]]
        utilities = [
            [20, 40, 60],
            [20, 60, 40],
            [40, 20, 60]]
        game_configuration = GameConfiguration(
            money_amounts,
            endowments,
            utilities,
            1
        )
        game = Game(game_configuration)

        # not enough money: amount + fee > balance of player 0
        buyer_id = 0
        seller_id = 1
        amount = 20
        quantities_by_good = {}
        invalid_transaction = GameTransaction(buyer_id, seller_id, amount, quantities_by_good)

        # transaction is invalide because buyer_balance < amount + fee
        assert not game.is_transaction_valid(invalid_transaction)

    def test_transaction_invalid_if_seller_does_not_have_enough_quantities(self):
        """Test that a transaction is invalid if the seller does not have enough quantities."""

        money_amounts = [20, 20, 20]
        endowments = [
            [1, 1, 0],
            [1, 0, 0],
            [0, 1, 2]]
        utilities = [
            [20, 40, 60],
            [20, 60, 40],
            [40, 20, 60]]
        fee = 1
        game_configuration = GameConfiguration(
            money_amounts,
            endowments,
            utilities,
            fee
        )
        game = Game(game_configuration)

        invalid_transaction = GameTransaction(0, 1, 10, {1: 1})
        assert not game.is_transaction_valid(invalid_transaction)

    def test_generate_game(self):
        """Test the game generation algorithm."""

        money_amounts = [20, 20, 20]  # type: List[int]
        score_values = {20, 40, 60}  # type: Set[int]
        fee = 1

        game = Game.generate_game(money_amounts, score_values, fee)

        # please look at the assertions in tac.game.GameConfiguration._check_consistency()

    def test_get_game_data_from_agent_label(self):
        """Test that the getter of game states by agent label works as expected."""

        money_amounts = [20, 20]
        endowments = [
            [0, 1],
            [1, 0]
        ]
        utilities = [
            [20, 40],
            [40, 20]
        ]
        fee = 1
        game_configuration = GameConfiguration(money_amounts, endowments, utilities, fee, ["agent_01", "agent_02"])
        game = Game(game_configuration)

        actual_game_state_0 = game.get_game_data_from_agent_label("agent_01")
        actual_game_state_1 = game.get_game_data_from_agent_label("agent_02")

        expected_game_state_0 = GameState(20, [0, 1], [20, 40])
        expected_game_state_1 = GameState(20, [1, 0], [40, 20])

        assert actual_game_state_0 == expected_game_state_0
        assert actual_game_state_1 == expected_game_state_1

    def test_to_dict(self):
        """Test that conversion into dict works as expected."""

        money_amounts = [20, 20]
        endowments = [
            [0, 1],
            [1, 0]]
        utilities = [
            [20, 40],
            [40, 20]]
        fee = 1
        game_configuration = GameConfiguration(
            money_amounts,
            endowments,
            utilities,
            fee
        )
        game = Game(game_configuration)

        game_transaction_1 = GameTransaction(0, 1, 10, {0: 1})
        game_transaction_2 = GameTransaction(1, 0, 10, {1: 1})
        game.settle_transaction(game_transaction_1)
        game.settle_transaction(game_transaction_2)

        actual_game_dict = game.to_dict()
        expected_game_dict = {
            "configuration": game_configuration.to_dict(),
            "transactions": [
                game_transaction_1.to_dict(),
                game_transaction_2.to_dict()
            ]
        }

        assert actual_game_dict == expected_game_dict

    def test_from_dict(self):
        """Test that conversion from dict works as expected."""
        money_amounts = [20, 20, 20]
        endowments = [
            [1, 1, 0],
            [1, 0, 0],
            [0, 1, 2]
        ]
        utilities = [
            [20, 40, 60],
            [20, 60, 40],
            [40, 20, 60]
        ]
        fee = 1
        agent_labels = ["agent_01", "agent_02", "agent_03"]

        expected_game = Game(GameConfiguration(money_amounts, endowments, utilities, fee, agent_labels))
        game_transaction_1 = GameTransaction(0, 1, 10, {0: 1})
        game_transaction_2 = GameTransaction(1, 0, 10, {1: 1})
        expected_game.settle_transaction(game_transaction_1)
        expected_game.settle_transaction(game_transaction_2)

        actual_game = Game.from_dict(expected_game.to_dict())

        assert actual_game == expected_game

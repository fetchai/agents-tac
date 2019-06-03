import pytest

from tac.protocol import Register, Unregister, Transaction, Registered, Unregistered, TransactionConfirmation, Error, \
    GameData, Request, Response, ErrorCode, Cancelled, GetStateUpdate, StateUpdate


class TestRequest:

    class TestRegister:

        def test_serialization_deserialization(self):
            """Test that serialization and deserialization gives the same result."""
            expected_msg = Register("public_key", "agent_name")
            actual_msg = Request.from_pb(expected_msg.serialize(), "public_key")

            assert expected_msg == actual_msg

    class TestUnregister:

        def test_serialization_deserialization(self):
            """Test that serialization and deserialization gives the same result."""
            expected_msg = Unregister("public_key")
            actual_msg = Request.from_pb(expected_msg.serialize(), "public_key")

            assert expected_msg == actual_msg

    class TestTransaction:

        def test_serialization_deserialization(self):
            """Test that serialization and deserialization gives the same result."""
            expected_msg = Transaction("transaction_id", True, "seller", 10, {'tac_good_0': 1, 'tac_good_1': 1},
                                       "public_key")
            actual_msg = Request.from_pb(expected_msg.serialize(), "public_key")

            assert expected_msg == actual_msg

    class TestGetStateUpdate:

        def test_serialization_deserialization(self):
            """Test that serialization and deserialization gives the same result."""
            expected_msg = GetStateUpdate("public_key")
            actual_msg = Request.from_pb(expected_msg.serialize(), "public_key")

            assert expected_msg == actual_msg


class TestResponse:

    class TestRegistered:

        def test_serialization_deserialization(self):
            """Test that serialization and deserialization gives the same result."""
            expected_msg = Registered("public_key")
            actual_msg = Response.from_pb(expected_msg.serialize(), "public_key")

            assert expected_msg == actual_msg

    class TestUnregistered:

        def test_serialization_deserialization(self):
            """Test that serialization and deserialization gives the same result."""
            expected_msg = Unregistered("public_key")
            actual_msg = Response.from_pb(expected_msg.serialize(), "public_key")

            assert expected_msg == actual_msg

    class TestCancelled:

        def test_serialization_deserialization(self):
            """Test that serialization and deserialization gives the same result."""
            expected_msg = Cancelled("public_key")
            actual_msg = Response.from_pb(expected_msg.serialize(), "public_key")

            assert expected_msg == actual_msg

    class TestError:

        @pytest.mark.parametrize("error_code", list(ErrorCode))
        def test_serialization_deserialization(self, error_code):
            """Test that serialization and deserialization gives the same result."""
            expected_msg = Error("public_key", error_code, "this is an error message.")
            actual_msg = Response.from_pb(expected_msg.serialize(), "public_key")

            assert expected_msg == actual_msg

    class TestGameData:

        def test_serialization_deserialization(self):
            """Test that serialization and deserialization gives the same result."""
            expected_msg = GameData("public_key", 10, [1, 1, 2], [0.04, 0.80, 0.16], 3, 3, 1.0, ['tac_agent_0_pbk', 'tac_agent_1_pbk', 'tac_agent_2_pbk'], ['tac_agent_0', 'tac_agent_1', 'tac_agent_2'], ['tag_good_0', 'tag_good_1', 'tag_good_2'])
            actual_msg = Response.from_pb(expected_msg.serialize(), "public_key")

            assert expected_msg == actual_msg

    class TestTransactionConfirmation:

        def test_serialization_deserialization(self):
            """Test that serialization and deserialization gives the same result."""
            expected_msg = TransactionConfirmation("public_key", "transaction_id")
            actual_msg = Response.from_pb(expected_msg.serialize(), "public_key")

            assert expected_msg == actual_msg

    class TestStateUpdate:

        def test_serialization_deserialization(self):
            """Test that serialization and deserialization gives the same result."""
            game_state = GameData("public_key", 10, [1, 1, 2], [0.04, 0.80, 0.16], 3, 3, 1.0, ['tac_agent_0_pbk', 'tac_agent_1_pbk', 'tac_agent_2_pbk'], ['tac_agent_0', 'tac_agent_1', 'tac_agent_2'], ['tag_good_0', 'tag_good_1', 'tag_good_2'])
            transactions = [Transaction("transaction_id", True, "seller", 10.0, {"good_01": 1}, "public_key")]

            expected_msg = StateUpdate("public_key", game_state, transactions)
            actual_msg = Response.from_pb(expected_msg.serialize(), "public_key")

            assert expected_msg == actual_msg

import pytest

from tac.protocol import Register, Unregister, Transaction, Registered, Unregistered, TransactionConfirmation, Error, \
    GameData, Request, Response, ErrorCode, Cancelled, GetStateUpdate, StateUpdate
from tac.helpers.crypto import Crypto


class TestRequest:

    class TestRegister:

        def test_serialization_deserialization(self):
            """Test that serialization and deserialization gives the same result."""
            crypto = Crypto()
            expected_msg = Register(crypto.public_key, crypto, "agent_name")
            actual_msg = Request.from_pb(expected_msg.serialize(), crypto.public_key, crypto)

            assert expected_msg == actual_msg

    class TestUnregister:

        def test_serialization_deserialization(self):
            """Test that serialization and deserialization gives the same result."""
            crypto = Crypto()
            expected_msg = Unregister(crypto.public_key, crypto)
            actual_msg = Request.from_pb(expected_msg.serialize(), crypto.public_key, crypto)

            assert expected_msg == actual_msg

    class TestTransaction:

        def test_serialization_deserialization(self):
            """Test that serialization and deserialization gives the same result."""
            crypto = Crypto()
            expected_msg = Transaction("transaction_id", True, "seller", 10, {'tac_good_0': 1, 'tac_good_1': 1},
                                       crypto.public_key, crypto)
            actual_msg = Request.from_pb(expected_msg.serialize(), crypto.public_key, crypto)

            assert expected_msg == actual_msg

    class TestGetStateUpdate:

        def test_serialization_deserialization(self):
            """Test that serialization and deserialization gives the same result."""
            crypto = Crypto()
            expected_msg = GetStateUpdate(crypto.public_key, crypto)
            actual_msg = Request.from_pb(expected_msg.serialize(), crypto.public_key, crypto)

            assert expected_msg == actual_msg


class TestResponse:

    class TestRegistered:

        def test_serialization_deserialization(self):
            """Test that serialization and deserialization gives the same result."""
            crypto = Crypto()
            expected_msg = Registered(crypto.public_key, crypto)
            actual_msg = Response.from_pb(expected_msg.serialize(), crypto.public_key, crypto)

            assert expected_msg == actual_msg

    class TestUnregistered:

        def test_serialization_deserialization(self):
            """Test that serialization and deserialization gives the same result."""
            crypto = Crypto()
            expected_msg = Unregistered(crypto.public_key, crypto)
            actual_msg = Response.from_pb(expected_msg.serialize(), crypto.public_key, crypto)

            assert expected_msg == actual_msg

    class TestCancelled:

        def test_serialization_deserialization(self):
            """Test that serialization and deserialization gives the same result."""
            crypto = Crypto()
            expected_msg = Cancelled(crypto.public_key, crypto)
            actual_msg = Response.from_pb(expected_msg.serialize(), crypto.public_key, crypto)

            assert expected_msg == actual_msg

    class TestError:

        @pytest.mark.parametrize("error_code", list(ErrorCode))
        def test_serialization_deserialization(self, error_code):
            """Test that serialization and deserialization gives the same result."""
            crypto = Crypto()
            expected_msg = Error(crypto.public_key, crypto, error_code, "this is an error message.")
            actual_msg = Response.from_pb(expected_msg.serialize(), crypto.public_key, crypto)

            assert expected_msg == actual_msg

    class TestGameData:

        def test_serialization_deserialization(self):
            """Test that serialization and deserialization gives the same result."""
            crypto = Crypto()
            expected_msg = GameData(crypto.public_key, crypto, 10, [1, 1, 2], [0.04, 0.80, 0.16], 3, 3, 1.0, ['tac_agent_0_pbk', 'tac_agent_1_pbk', 'tac_agent_2_pbk'], ['tac_agent_0', 'tac_agent_1', 'tac_agent_2'], ['tag_good_0', 'tag_good_1', 'tag_good_2'])
            actual_msg = Response.from_pb(expected_msg.serialize(), crypto.public_key, crypto)

            assert expected_msg == actual_msg

    class TestTransactionConfirmation:

        def test_serialization_deserialization(self):
            """Test that serialization and deserialization gives the same result."""
            crypto = Crypto()
            expected_msg = TransactionConfirmation(crypto.public_key, crypto, "transaction_id")
            actual_msg = Response.from_pb(expected_msg.serialize(), crypto.public_key, crypto)

            assert expected_msg == actual_msg

    class TestStateUpdate:

        def test_serialization_deserialization(self):
            """Test that serialization and deserialization gives the same result."""
            crypto = Crypto()
            game_state = GameData(crypto.public_key, crypto, 10, [1, 1, 2], [0.04, 0.80, 0.16], 3, 3, 1.0, ['tac_agent_0_pbk', 'tac_agent_1_pbk', 'tac_agent_2_pbk'], ['tac_agent_0', 'tac_agent_1', 'tac_agent_2'], ['tag_good_0', 'tag_good_1', 'tag_good_2'])
            transactions = [Transaction("transaction_id", True, "seller", 10.0, {"good_01": 1}, crypto.public_key, crypto)]

            expected_msg = StateUpdate(crypto.public_key, crypto, game_state, transactions)
            actual_msg = Response.from_pb(expected_msg.serialize(), crypto.public_key, crypto)

            assert expected_msg == actual_msg

import pytest

from tac.protocol import Register, Unregister, Transaction, Registered, Unregistered, TransactionConfirmation, Error, \
    GameData, Request, Response, ErrorCode, Cancelled


class TestRequest:

    class TestRegister:

        def test_serialization_deserialization(self):
            """Test that serialization and deserialization gives the same result."""
            expected_msg = Register()
            actual_msg = Request.from_pb(expected_msg.serialize())

            assert expected_msg == actual_msg

    class TestUnregister:

        def test_serialization_deserialization(self):
            """Test that serialization and deserialization gives the same result."""
            expected_msg = Unregister()
            actual_msg = Request.from_pb(expected_msg.serialize())

            assert expected_msg == actual_msg

    class TestTransaction:

        def test_serialization_deserialization(self):
            """Test that serialization and deserialization gives the same result."""
            expected_msg = Transaction("transaction_id", True, "seller", 10, {'tac_good_0': 1, 'tac_good_1': 1})
            actual_msg = Request.from_pb(expected_msg.serialize())

            assert expected_msg == actual_msg


class TestResponse:

    class TestRegistered:

        def test_serialization_deserialization(self):
            """Test that serialization and deserialization gives the same result."""
            expected_msg = Registered()
            actual_msg = Response.from_pb(expected_msg.serialize())

            assert expected_msg == actual_msg

    class TestUnregistered:

        def test_serialization_deserialization(self):
            """Test that serialization and deserialization gives the same result."""
            expected_msg = Unregistered()
            actual_msg = Response.from_pb(expected_msg.serialize())

            assert expected_msg == actual_msg

    class TestCancelled:

        def test_serialization_deserialization(self):
            """Test that serialization and deserialization gives the same result."""
            expected_msg = Cancelled()
            actual_msg = Response.from_pb(expected_msg.serialize())

            assert expected_msg == actual_msg

    class TestError:

        @pytest.mark.parametrize("error_code", list(ErrorCode))
        def test_serialization_deserialization(self, error_code):
            """Test that serialization and deserialization gives the same result."""
            expected_msg = Error(error_code, "this is an error message.")
            actual_msg = Response.from_pb(expected_msg.serialize())

            assert expected_msg == actual_msg

    class TestGameData:

        def test_serialization_deserialization(self):
            """Test that serialization and deserialization gives the same result."""
            expected_msg = GameData(10, [1, 1, 2], [0.04, 0.80, 0.16], 3, 3, 1.0, ['tac_agent_0', 'tac_agent_1', 'tac_agent_2'], ['tag_good_0', 'tag_good_1', 'tag_good_2'])
            actual_msg = Response.from_pb(expected_msg.serialize())

            assert expected_msg == actual_msg

    class TestTransactionConfirmation:

        def test_serialization_deserialization(self):
            """Test that serialization and deserialization gives the same result."""
            expected_msg = TransactionConfirmation("transaction_id")
            actual_msg = Response.from_pb(expected_msg.serialize())

            assert expected_msg == actual_msg

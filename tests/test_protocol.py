from tac.protocol import Register, Unregister, Transaction, Registered, Unregistered, TransactionConfirmation, Error, \
    GameData, Request, Response


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
            expected_msg = Transaction("transaction_id", True, "seller", 10, {0: 1, 1: 1})
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

    class TestError:

        def test_serialization_deserialization(self):
            """Test that serialization and deserialization gives the same result."""
            expected_msg = Error("this is an error message.")
            actual_msg = Response.from_pb(expected_msg.serialize())

            assert expected_msg == actual_msg

    class TestGameData:

        def test_serialization_deserialization(self):
            """Test that serialization and deserialization gives the same result."""
            expected_msg = GameData(10, [0, 1, 2], [20, 40, 60], 1)
            actual_msg = Response.from_pb(expected_msg.serialize())

            assert expected_msg == actual_msg

    class TestTransactionConfirmation:

        def test_serialization_deserialization(self):
            """Test that serialization and deserialization gives the same result."""
            expected_msg = TransactionConfirmation("transaction_id")
            actual_msg = Response.from_pb(expected_msg.serialize())

            assert expected_msg == actual_msg

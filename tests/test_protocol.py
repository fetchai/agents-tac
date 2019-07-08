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

"""This module contains the tests of the protocol module."""

import pytest

from tac.platform.protocol import Register, Unregister, Transaction, TransactionConfirmation, Error, \
    GameData, Request, Response, ErrorCode, Cancelled, GetStateUpdate, StateUpdate
from tac.helpers.crypto import Crypto


class TestRequest:
    """Class to test the Request classes."""

    class TestRegister:
        """Class to test the Register class."""

        def test_serialization_deserialization(self):
            """Test that serialization and deserialization gives the same result."""
            crypto = Crypto()
            expected_msg = Register(crypto.public_key, crypto, "tac_agent_0")
            actual_msg = Request.from_pb(expected_msg.serialize(), crypto.public_key, crypto)

            assert expected_msg == actual_msg

    class TestUnregister:
        """Class to test the Unregister class."""

        def test_serialization_deserialization(self):
            """Test that serialization and deserialization gives the same result."""
            crypto = Crypto()
            expected_msg = Unregister(crypto.public_key, crypto)
            actual_msg = Request.from_pb(expected_msg.serialize(), crypto.public_key, crypto)

            assert expected_msg == actual_msg

    class TestTransaction:
        """Class to test the Transaction class."""

        def test_serialization_deserialization(self):
            """Test that serialization and deserialization gives the same result."""
            crypto = Crypto()
            expected_msg = Transaction("transaction_id", True, "seller", 10, {'tac_good_0_pbk': 1, 'tac_good_1_pbk': 1},
                                       crypto.public_key, crypto)
            actual_msg = Request.from_pb(expected_msg.serialize(), crypto.public_key, crypto)

            assert expected_msg == actual_msg

    class TestGetStateUpdate:
        """Class to test the GetStateUpdate class."""

        def test_serialization_deserialization(self):
            """Test that serialization and deserialization gives the same result."""
            crypto = Crypto()
            expected_msg = GetStateUpdate(crypto.public_key, crypto)
            actual_msg = Request.from_pb(expected_msg.serialize(), crypto.public_key, crypto)

            assert expected_msg == actual_msg


class TestResponse:
    """Class to test the Response classes."""

    class TestCancelled:
        """Class to test the Cancelled class."""

        def test_serialization_deserialization(self):
            """Test that serialization and deserialization gives the same result."""
            crypto = Crypto()
            expected_msg = Cancelled(crypto.public_key, crypto)
            actual_msg = Response.from_pb(expected_msg.serialize(), crypto.public_key, crypto)

            assert expected_msg == actual_msg

    class TestError:
        """Class to test the Error class."""

        @pytest.mark.parametrize("error_code", list(ErrorCode))
        def test_serialization_deserialization(self, error_code):
            """Test that serialization and deserialization gives the same result."""
            crypto = Crypto()
            expected_msg = Error(crypto.public_key, crypto, error_code, "this is an error message.")
            actual_msg = Response.from_pb(expected_msg.serialize(), crypto.public_key, crypto)

            assert expected_msg == actual_msg

    class TestGameData:
        """Class to test the GameData class."""

        def test_serialization_deserialization(self):
            """Test that serialization and deserialization gives the same result."""
            crypto = Crypto()
            expected_msg = GameData(crypto.public_key, crypto, 10, [1, 1, 2], [0.04, 0.80, 0.16], 3, 3, 1.0, {'tac_agent_0_pbk': 'tac_agent_0', 'tac_agent_1_pbk': 'tac_agent_1', 'tac_agent_2_pbk': 'tac_agent_2'}, {'tag_good_0_pbk': 'tag_good_0', 'tag_good_1_pbk': 'tag_good_1', 'tag_good_2_pbk': 'tag_good_2'})
            actual_msg = Response.from_pb(expected_msg.serialize(), crypto.public_key, crypto)

            assert expected_msg == actual_msg

    class TestTransactionConfirmation:
        """Class to test the TransactionConfirmation class."""

        def test_serialization_deserialization(self):
            """Test that serialization and deserialization gives the same result."""
            crypto = Crypto()
            expected_msg = TransactionConfirmation(crypto.public_key, crypto, "transaction_id")
            actual_msg = Response.from_pb(expected_msg.serialize(), crypto.public_key, crypto)

            assert expected_msg == actual_msg

    class TestStateUpdate:
        """Class to test the StateUpdate class."""

        def test_serialization_deserialization(self):
            """Test that serialization and deserialization gives the same result."""
            crypto = Crypto()
            game_state = GameData(crypto.public_key, crypto, 10, [1, 1, 2], [0.04, 0.80, 0.16], 3, 3, 1.0, {'tac_agent_0_pbk': 'tac_agent_0', 'tac_agent_1_pbk': 'tac_agent_1', 'tac_agent_2_pbk': 'tac_agent_2'}, {'tag_good_0_pbk': 'tag_good_0', 'tag_good_1_pbk': 'tag_good_1', 'tag_good_2_pbk': 'tag_good_2'})
            transactions = [Transaction("transaction_id", True, "seller", 10.0, {"tac_good_0_pbk": 1}, crypto.public_key, crypto)]

            expected_msg = StateUpdate(crypto.public_key, crypto, game_state, transactions)
            actual_msg = Response.from_pb(expected_msg.serialize(), crypto.public_key, crypto)

            assert expected_msg == actual_msg

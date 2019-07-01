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

"""This module contains miscellaneous tests."""

from tac.helpers.misc import generate_transaction_id


def test_generate_transaction_id():
    """Test that the transaction id is correctly generated."""
    expected_result = "buyer_pbk_seller_pbk_12345"
    actual_result = generate_transaction_id("buyer_pbk", "seller_pbk", 12345, False)

    assert actual_result == expected_result

    expected_result = "seller_pbk_buyer_pbk_12345"
    actual_result = generate_transaction_id("buyer_pbk", "seller_pbk", 12345, True)

    assert actual_result == expected_result

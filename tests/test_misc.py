# -*- coding: utf-8 -*-
from tac.helpers.misc import generate_transaction_id


def test_generate_transaction_id():
    expected_result = "buyer_pbk_seller_pbk_12345"
    actual_result = generate_transaction_id("buyer_pbk", "seller_pbk", 12345, False)

    assert actual_result == expected_result

    expected_result = "seller_pbk_buyer_pbk_12345"
    actual_result = generate_transaction_id("buyer_pbk", "seller_pbk", 12345, True)

    assert actual_result == expected_result

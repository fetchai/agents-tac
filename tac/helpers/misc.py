# -*- coding: utf-8 -*-

# ------------------------------------------------------------------------------
#
#   Copyright 2018-2019 Fetch.AI Limited
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------
import logging
import random
from typing import List

import numpy as np
from oef.schema import AttributeSchema, DataModel, Description

logger = logging.getLogger("tac")


class TacError(Exception):
    """General purpose exception to detect exception associated with the logic of the TAC application."""


def callback(fut):
    """Callback to audit exceptions from asyncio tasks."""
    try:
        _ = fut.result()
    except Exception as e:
        logger.exception('Unexpected error')
        raise e


def generate_transaction_id(seller, buyer, dialogue_id):
    transaction_id = "{}_{}_{}".format(buyer, seller, dialogue_id)
    return transaction_id


def sample_good_instance(n, g) -> int:
    """Sample the number of instances for a good.
    :param n: the number of agents
    :param g: the tuning parameter
    :return the number of instances I sampled.
    """
    delta = n/g
    a = n - delta
    b = n + delta
    # Return random integer in range [a, b]
    nb_instances = round(np.random.uniform(a, b))
    return nb_instances


def compute_allocation(n: int, h: int) -> List[int]:
    """
    Compute an allocation (defined above).
    :param n: the number of agents.
    :param h: the number of instances to allocate.
    :return: the allocation (a vector of 0s and 1s
    """
    allocation = [0] * n
    for i in random.sample(range(n), h):
        allocation[i] = 1
    return allocation


def compute_endowment_of_good(n, nb_instances) -> List[int]:
    """
    Compute the allocation for all the agent of a single good.
    :param n: the number of agents.
    :param nb_instances: the number of instances of the good.
    :return: the endowment of good j for all the agents.
    """
    I_j = nb_instances
    h_1, h_2 = (I_j // 2, I_j // 2) if I_j % 2 == 0 else (I_j // 2, I_j // 2 + 1)
    a_1, a_2 = [compute_allocation(n, h_1), compute_allocation(n, h_2)]

    endowment = [a_1[idx] + a_2[idx] for idx in range(n)]

    return endowment


def _build_seller_datamodel(nb_goods: int) -> DataModel:
    """
    Build a data model for sellers.

    :param nb_goods: the number of goods.
    :return: the seller data model.
    """
    goods_quantities_attributes = [AttributeSchema("good_{:02d}".format(i), int, True) for i in range(nb_goods)]
    price_attribute = AttributeSchema("price", int, False)
    data_model = DataModel("tac_seller", goods_quantities_attributes + [price_attribute])
    return data_model


def get_baseline_seller_description(game_state: 'GameState') -> Description:
    """
    Get the TAC seller description, following a baseline policy.
    That is, a description with the following structure:
    >>> {
    ...     "good_01": 1,
    ...     "good_02": 0,
    ...     #...
    ...
    ... }
     where the keys indicate the good and the values the quantity that the seller wants to sell.

     The baseline agent decides to sell everything in excess, but keeping the goods that

    :return: the description to advertise on the Service Directory.
    """
    seller_data_model = _build_seller_datamodel(game_state.nb_goods)
    desc = Description({"good_{:02d}".format(i): q
                        for i, q in enumerate(game_state.get_excess_goods_quantities())},
                       data_model=seller_data_model)
    return desc

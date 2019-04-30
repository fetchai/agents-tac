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
import datetime
import logging
import random
from typing import List, Set, Optional

import dateutil.parser
import math
import numpy as np
from oef.query import Query, Constraint, GtEq, Or
from oef.schema import AttributeSchema, DataModel, Description


logger = logging.getLogger("tac")
TAC_SELLER_DATAMODEL_NAME = "tac_seller"
TAC_BUYER_DATAMODEL_NAME = "tac_buyer"


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


def format_good_attribute_name(good_id: int, nb_goods: int) -> str:
    """Format the name of the attribute associated to a good id.

    E.g.:

    >>> format_good_attribute_name(2, 10)
    'good_2'
    >>> format_good_attribute_name(2, 100)
    'good_02'
    >>> format_good_attribute_name(2, 101)
    'good_002'

    :param good_id: the good id.
    :param nb_goods: the overall number of goods.
    :return: the formatted name.
    """
    max_number_of_digits = math.ceil(math.log10(nb_goods))
    string_format = "good_{:0" + str(max_number_of_digits) + "}"
    result = string_format.format(good_id)
    return result


def from_good_attribute_name_to_good_id(good_id_str: str) -> 1:
    """
    From 'good_[0-9]+' to the associated good id.

    >>> from_good_attribute_name_to_good_id("good_001")
    1
    >>> from_good_attribute_name_to_good_id("good_9999")
    9999


    :param good_id_str: the good id in the format for attribute names.
    :return: the good id.
    """
    offset = len("good_")
    return int(good_id_str[offset:])


def sample_good_instance(a: int, b: int) -> int:
    """Sample the number of instances for a good.

    :param a: the lower bound of the uniform distribution
    :param b: the uper bound of the uniform distribution
    :return the number of instances I sampled.
    """
    # Return random integer in range [a, b]
    nb_instances = round(np.random.uniform(a, b))
    return nb_instances


def compute_allocation(nb_agents: int, h: int) -> List[int]:
    """
    Compute an allocation (defined above).
    :param nb_agents: the number of agents.
    :param h: the number of instances to allocate.
    :return: the allocation (a vector of 0s and 1s
    """
    allocation = [0] * nb_agents
    for i in random.sample(range(nb_agents), h):
        allocation[i] = 1
    return allocation


def generate_instances_per_good(nb_goods: int, nb_agents: int, lower_bound_factor: int, upper_bound_factor: int) -> List[int]:
    """
    Compute the vector of good instances available in the game.
    An element of the vector at index j determines the number of instances of good j in the game.
    :param nb_goods: the number of goods.
    :param nb_agents: the number of agents.
    :param lower_bound_factor: the lower bound factor of the uniform distribution
    :param upper_bound_factor: the upper bound factor of the uniform distribution
    :return: the vector of good instances.
    """
    a = nb_agents - round(nb_agents / float(lower_bound_factor))
    b = nb_agents + round(nb_agents / float(upper_bound_factor))
    return [sample_good_instance(a, b) for _ in range(nb_goods)]


def generate_endowment_of_good(nb_agents: int, nb_instances: int) -> List[int]:
    """
    Compute the allocation for all the agent of a single good.
    :param nb_agents: the number of agents.
    :param nb_instances: the number of instances of the good.
    :return: the endowment of good j for all the agents.
    """
    I_j = nb_instances
    h_1, h_2 = (I_j // 2, I_j // 2) if I_j % 2 == 0 else (I_j // 2, I_j // 2 + 1)
    a_1, a_2 = [compute_allocation(nb_agents, h_1), compute_allocation(nb_agents, h_2)]

    endowment = [a_1[idx] + a_2[idx] for idx in range(nb_agents)]

    return endowment


def generate_endowments(nb_goods: int, nb_agents: int, lower_bound_factor: int, upper_bound_factor: int) -> List[List[int]]:
    """
    Compute endowments per agent. That is, a matrix of shape (nb_agents, nb_goods)

    :param nb_goods: the number of goods.
    :param nb_agents: the number of agents.
    :param lower_bound_factor: the lower bound of the uniform distribution for the sampling of the good instance number.
    :param upper_bound_factor: the upper bound of the uniform distribution for the sampling of the good instance number.
    :return: the endowments matrix.
    """
    instances_per_good = generate_instances_per_good(nb_goods, nb_agents, lower_bound_factor, upper_bound_factor) # type: List[int]
    # compute endowment matrix per good. The shape is (nb_goods, nb_agents).
    # Row i contains the holdings for every agent j.
    endowments_by_good = [generate_endowment_of_good(nb_agents, I_j) for I_j in instances_per_good] # type: List[List[int]]
    # transpose the matrix.
    endowments = np.asarray(endowments_by_good).T.tolist()
    return endowments


def generate_utilities(nb_agents: int, nb_goods: int) -> List[List[int]]:
    """
    Compute the preference matrix. That is, a generic element e_ij is the utility of good j for agent i.

    :param nb_agents: the number of agents.
    :param nb_goods: the number of goods.
    :return: the preference matrix.
    """
    scores = set(range(nb_goods))  # type: Set[int]
    # matrix where each row is in the same order.
    temporary_matrix = [list(scores)] * nb_agents
    # compute random preferences (i.e. permute every preference list randomly).
    preferences = list(map(lambda x: random.sample(x, len(x)), temporary_matrix))
    return preferences


def generate_initial_money_amounts(nb_agents: int, money_endowment: int) -> List[int]:
    """
    Compute the initial money amounts for each agent.

    :param nb_agents: number of agents.
    :param money_endowment: money endowment per agent.
    :return: the list of initial money amounts.
    """
    return [money_endowment] * nb_agents


def build_datamodel(nb_goods: int, seller: bool) -> DataModel:
    """
    Build a data model for buyers or sellers.

    :param nb_goods: the number of goods.
    :param seller: bool indicating whether a seller or buyer data model
    :return: the data model.
    """
    goods_quantities_attributes = [AttributeSchema(format_good_attribute_name(i, nb_goods), int, False)
                                   for i in range(nb_goods)]
    price_attribute = AttributeSchema("price", int, False)
    description = TAC_SELLER_DATAMODEL_NAME if seller else TAC_BUYER_DATAMODEL_NAME
    data_model = DataModel(description, goods_quantities_attributes + [price_attribute])
    return data_model


def get_goods_quantities_description(good_quantities: List[int], is_seller: bool) -> Description:
    """
    Get the TAC seller description, following a baseline policy.
    That is, a description with the following structure:
    >>> desciption = {
    ...     "good_01": 1,
    ...     "good_02": 0,
    ...     #...
    ...
    ... }
    >>>

     where the keys indicate the good and the values the quantity that the seller wants to sell.

     The baseline agent decides to sell everything in excess, but keeping the goods that

     >>> desc = get_goods_quantities_description([0, 0, 1, 2], True)
     >>> desc.data_model.name == TAC_SELLER_DATAMODEL_NAME
     True
     >>> desc.values == {
     ...    "good_0": 0,
     ...    "good_1": 0,
     ...    "good_2": 1,
     ...    "good_3": 2,
     ...}
     True

    :param good_quantities: the quantities per good.
    :param is_seller: True if the description is of a seller, False if it's of a buyer.
    :return: the description to advertise on the Service Directory.
    """
    nb_goods = len(good_quantities)
    data_model = build_datamodel(nb_goods, seller=is_seller)
    desc = Description({format_good_attribute_name(i, nb_goods): q for i, q in enumerate(good_quantities)},
                       data_model=data_model)
    return desc


def build_query(good_ids: Set[int], seller: bool, nb_goods: Optional[int] = None) -> Query:
    """
    Build the query that the buyer can send to look for goods.

    In particular, if the needed good ids are {0, 2, 3}, the resulting constraint expression is:

        good_0 >= 1 OR good_2 >= 1 OR good_3 >= 1

    That is, the OEF will return all the sellers that have at least one of the good in the query
    (assuming that the sellers are registered with the data model for baseline sellers.

    :param good_ids: the good ids to put in the query.
    :param seller: bool indicating whether it's a seller or buyer query
    :param nb_goods: the total number of goods (to build the data model, optional)
    :return: the query.
    """
    data_model = None if nb_goods is None else build_datamodel(nb_goods, seller)
    constraints = [Constraint(format_good_attribute_name(good_id, nb_goods), GtEq(1)) for good_id in good_ids]

    if len(good_ids) > 1:
        constraints = [Or(constraints)]

    query = Query(constraints, model=data_model)
    return query


def from_iso_format(date_string: str) -> datetime.datetime:
    """
    From string representation in ISO format to a datetime.datetime object
    :param date_string: the string to parse.
    :return: the datetime object.
    """
    return dateutil.parser.parse(date_string)

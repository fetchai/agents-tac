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


def generate_transaction_id(buyer, seller, dialogue_id):
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


def generate_endowments(nb_goods: int, nb_agents: int, uniform_lower_bound_factor: int, uniform_upper_bound_factor: int) -> List[List[int]]:
    """
    Compute endowments per agent. That is, a matrix of shape (nb_agents, nb_goods)

    :param nb_goods: the number of goods.
    :param nb_agents: the number of agents.
    :param uniform_lower_bound_factor: the lower bound of the uniform distribution for the sampling of the good instance number.
    :param uniform_upper_bound_factor: the upper bound of the uniform distribution for the sampling of the good instance number.
    :return: the endowments matrix.
    """
    # sample good instances
    instances_per_good = _sample_good_instances(nb_agents, nb_goods,
                                                uniform_lower_bound_factor, uniform_upper_bound_factor)
    # each agent receives at least one good
    endowments = [[1] * nb_goods for _ in range(nb_agents)]
    # randomly assign additional goods to create differences
    for good_id in range(nb_goods):
        for _ in range(instances_per_good[good_id] - nb_agents):
            agent_id = random.randint(0, nb_agents - 1)
            endowments[agent_id][good_id] += 1
    return endowments


def generate_utilities(nb_agents: int, nb_goods: int) -> List[List[float]]:
    """
    Compute the preference matrix. That is, a generic element e_ij is the utility of good j for agent i.

    :param nb_agents: the number of agents.
    :param nb_goods: the number of goods.
    :return: the preference matrix.
    """
    utilities = _sample_utility_function_params(nb_goods, nb_agents)
    return utilities


def _sample_utility_function_params(nb_goods: int, nb_agents: int, scaling_factor: float = 100.0) -> List[List[float]]:
    """
    Sample utility function params for each agent.
    :param nb_goods: the number of goods
    :param nb_agents: the number of agents
    :param scaling_factor: a scaling factor for all the utilities generated.
    :return: a matrix with utility function params for each agent
    """
    decimals = 4 if nb_goods < 100 else 8
    utility_function_params = []
    for i in range(nb_agents):
        random_integers = [random.randint(1, 101) for _ in range(nb_goods)]
        total = sum(random_integers)
        normalized_fractions = [round(i / float(total), decimals) for i in random_integers]
        if not sum(normalized_fractions) == 1.0:
            normalized_fractions[-1] = round(1.0 - sum(normalized_fractions[0:-1]), decimals)
        utility_function_params.append(normalized_fractions)

    # scale the utilities
    for i in range(len(utility_function_params)):
        for j in range(len(utility_function_params[i])):
            utility_function_params[i][j] *= scaling_factor

    return utility_function_params


def _sample_good_instances(nb_agents: int, nb_goods: int,
                           uniform_lower_bound_factor: int, uniform_upper_bound_factor: int) -> List[int]:
    """
    Sample the number of instances for a good.
    :param nb_agents: the number of agents
    :param uniform_lower_bound_factor: the lower bound factor of a uniform distribution
    :param uniform_upper_bound_factor: the upper bound factor of a uniform distribution
    :return: the number of instances I sampled.
    """
    a = nb_agents + nb_agents * uniform_lower_bound_factor
    b = nb_agents + nb_agents * uniform_upper_bound_factor
    # Return random integer in range [a, b]
    nb_instances = [round(np.random.uniform(a, b)) for _ in range(nb_goods)]
    return nb_instances


def generate_initial_money_amounts(nb_agents: int, money_endowment: int) -> List[int]:
    """
    Compute the initial money amounts for each agent.

    :param nb_agents: number of agents.
    :param money_endowment: money endowment per agent.
    :return: the list of initial money amounts.
    """
    return [money_endowment] * nb_agents


def logarithmic_utility(utility_function_params: List[float], good_bundle: List[int]) -> float:
    """
    Compute agent's utility given her utility function params and a good bundle.
    :param utility_function_params: utility function params of the agent
    :param good_bundle: a bundle of goods with the quantity for each good
    :return: utility value
    """
    goodwise_utility = [param * math.log(quantity) if quantity > 0 else -10000
                        for param, quantity in zip(utility_function_params, good_bundle)]
    return sum(goodwise_utility)

def marginal_utility(utility_function_params: List[float], current_holdings: List[int], delta_holdings: List[int]) -> float:
    """
    Compute agent's utility given her utility function params and a good bundle.
    :param utility_function_params: utility function params of the agent
    :param current_holdings: a list of goods with the quantity for each good
    :param delta_holdings: a list of goods with the quantity for each good (can be positive or negative)
    :return: utility difference between new and current utility
    """
    current_utility = logarithmic_utility(utility_function_params, current_holdings)
    new_holdings = [sum(x) for x in zip(current_holdings, delta_holdings)]
    new_utility = logarithmic_utility(utility_function_params, new_holdings)
    return new_utility - current_utility

def build_datamodel(nb_goods: int, seller: bool) -> DataModel:
    """
    Build a data model for buyers or sellers.

    :param nb_goods: the number of goods.
    :param seller: bool indicating whether a seller or buyer data model
    :return: the data model.
    """
    goods_quantities_attributes = [AttributeSchema(format_good_attribute_name(i, nb_goods), int, False)
                                   for i in range(nb_goods)]
    price_attribute = AttributeSchema("price", float, False)
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
     ...    "good_3": 2}
     ...
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

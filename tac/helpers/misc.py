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
from typing import List, Set

import dateutil.parser
import math
import numpy as np
from oef.query import Query, Constraint, GtEq, Or
from oef.schema import AttributeSchema, DataModel, Description


logger = logging.getLogger("tac")
TAC_SUPPLY_DATAMODEL_NAME = "tac_supply"
TAC_DEMAND_DATAMODEL_NAME = "tac_demand"


class TacError(Exception):
    """General purpose exception to detect exception associated with the logic of the TAC application."""


def generate_transaction_id(agent_pbk: str, origin: str, dialogue_id: int, agent_is_seller: bool) -> str:
    """
    Generate a transaction id.
    :param agent_pbk: the pbk of the agent.
    :param origin: the public key of the message sender.
    :param dialogue_id: the dialogue id
    :param agent_is_seller: boolean indicating
    :return: a transaction id
    """
    # the format is {buyer_pbk}_{seller_pbk}_{dialogue_id}
    if agent_is_seller:
        transaction_id = "{}_{}_{}".format(origin, agent_pbk, dialogue_id)
    else:
        transaction_id = "{}_{}_{}".format(agent_pbk, origin, dialogue_id)
    return transaction_id


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


def generate_utility_params(nb_agents: int, nb_goods: int) -> List[List[float]]:
    """
    Compute the preference matrix. That is, a generic element e_ij is the utility of good j for agent i.

    :param nb_agents: the number of agents.
    :param nb_goods: the number of goods.
    :return: the preference matrix.
    """
    utility_params = _sample_utility_function_params(nb_goods, nb_agents)
    return utility_params


def _sample_utility_function_params(nb_goods: int, nb_agents: int, scaling_factor: float = 100.0) -> List[List[float]]:
    """
    Sample utility function params for each agent.
    :param nb_goods: the number of goods
    :param nb_agents: the number of agents
    :param scaling_factor: a scaling factor for all the utility params generated.
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

    # scale the utility params
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


def build_datamodel(good_pbks: List[str], is_supply: bool) -> DataModel:
    """
    Build a data model for supply and demand (i.e. for offered or requested goods).

    :param good_pbks: the list of good pbks
    :param is_supply: Boolean indicating whether it is a supply or demand data model

    :return: the data model.
    """
    goods_quantities_attributes = [AttributeSchema(good_pbk, int, False)
                                   for good_pbk in good_pbks]
    price_attribute = AttributeSchema("price", float, False)
    description = TAC_SUPPLY_DATAMODEL_NAME if is_supply else TAC_DEMAND_DATAMODEL_NAME
    data_model = DataModel(description, goods_quantities_attributes + [price_attribute])
    return data_model


def get_goods_quantities_description(good_pbks: List[str], good_quantities: List[int], is_supply: bool) -> Description:
    """
    Get the TAC description for supply or demand.
    That is, a description with the following structure:
    >>> description = {
    ...     "tac_good_0": 1,
    ...     "tac_good_1": 0,
    ...     #...
    ...
    ... }
    >>>

     where the keys indicate the good_pbk and the values the quantity.

     >>> desc = get_goods_quantities_description(['tac_good_0', 'tac_good_1', 'tac_good_2', 'tac_good_3'], [0, 0, 1, 2], True)
     >>> desc.data_model.name == TAC_SUPPLY_DATAMODEL_NAME
     True
     >>> desc.values == {
     ...    "tac_good_0": 0,
     ...    "tac_good_1": 0,
     ...    "tac_good_2": 1,
     ...    "tac_good_3": 2}
     ...
     True

    :param good_pbks: the pbks of the goods.
    :param good_quantities: the quantities per good.
    :param is_supply: True if the description is indicating supply, False if it's indicating demand.

    :return: the description to advertise on the Service Directory.
    """
    data_model = build_datamodel(good_pbks, is_supply=is_supply)
    desc = Description({good_pbk: quantity for good_pbk, quantity in zip(good_pbks, good_quantities)},
                       data_model=data_model)
    return desc


def build_query(good_pbks: Set[int], is_searching_for_sellers: bool) -> Query:
    """
    Build the search query
        - to look for sellers if the agent is a buyer, or
        - to look for buyers if the agent is a seller.

    In particular, if the agent is a buyer and the demanded good pbks are {'tac_good_0', 'tac_good_2', 'tac_good_3'}, the resulting constraint expression is:

        tac_good_0 >= 1 OR tac_good_2 >= 1 OR tac_good_3 >= 1

    That is, the OEF will return all the sellers that have at least one of the good in the query
    (assuming that the sellers are registered with the data model specified).

    :param good_pbks: the good pbks to put in the query
    :param is_searching_for_sellers: Boolean indicating whether the query is for sellers (supply) or buyers (demand).

    :return: the query
    """
    data_model = None if good_pbks is None else build_datamodel(good_pbks, is_supply=is_searching_for_sellers)
    constraints = [Constraint(good_pbk, GtEq(1)) for good_pbk in good_pbks]

    if len(good_pbks) > 1:
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


def generate_pbks(nb_things: int, thing_name: str) -> List[str]:
    """
    Generate pbks for things.
    :param nb_things: the number of things.
    :return: a list of pbks.
    """
    max_number_of_digits = math.ceil(math.log10(nb_things))
    string_format = "tac_" + thing_name + "_{:0" + str(max_number_of_digits) + "}"
    return [string_format.format(i) for i in range(nb_things)]

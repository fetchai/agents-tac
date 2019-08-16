#!/usr/bin/env python3
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

"""This module contains helpers for platform."""

import math


def make_agent_name(agent_id: int, is_world_modeling: bool, nb_agents: int) -> str:
    """
    Make the name for baseline agents from an integer identifier.

    E.g.:

    >>> make_agent_name(2, False, 10)
    'tac_agent_2'
    >>> make_agent_name(2, False, 100)
    'tac_agent_02'
    >>> make_agent_name(2, False, 101)
    'tac_agent_002'

    :param agent_id: the agent id.
    :param is_world_modeling: the boolean indicated whether the baseline agent models the world around her or not.
    :param nb_agents: the overall number of agents.
    :return: the formatted name.
    :return: the string associated to the integer id.
    """
    max_number_of_digits = math.ceil(math.log10(nb_agents))
    if is_world_modeling:
        string_format = "tac_agent_{:0" + str(max_number_of_digits) + "}_wm"
    else:
        string_format = "tac_agent_{:0" + str(max_number_of_digits) + "}"
    result = string_format.format(agent_id)
    return result

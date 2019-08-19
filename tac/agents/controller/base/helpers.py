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
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------

"""This module contains the helpers methods for the controller agent."""

from typing import Dict
import math


def generate_good_pbk_to_name(nb_goods: int) -> Dict[str, str]:
    """
    Generate public keys for things.

    :param nb_goods: the number of things.
    :return: a dictionary mapping goods' public keys to names.
    """
    max_number_of_digits = math.ceil(math.log10(nb_goods))
    string_format = 'tac_good_{:0' + str(max_number_of_digits) + '}'
    return {string_format.format(i) + '_pbk': string_format.format(i) for i in range(nb_goods)}

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

"""Spawn several TAC agents."""
import os
from tac.platform.shared_sim_status import register_shared_dir

from tac.platform.simulation import parse_arguments, build_simulation_parameters, run

if __name__ == '__main__':
    register_shared_dir(os.path.join(os.path.dirname(__file__), '../../data/shared'))

    arguments = parse_arguments()
    simulation_parameters = build_simulation_parameters(arguments)
    run(simulation_parameters)

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
"""Register the resources with flask and set up the shared status file."""

import os

from flask_restful import Api

from .resources.sandboxes import SandboxList, Sandbox
from .resources.agents import Agent
from tac.platform.shared_sim_status import register_shared_dir, clear_temp_dir


def create_api(app):
    """Wrap the Flask app with the Flask-RESTful Api object."""
    api = Api(app, prefix='/api')

    api.add_resource(SandboxList, "/sandboxes")
    api.add_resource(Sandbox, "/sandboxes/<int:sandbox_id>")
    api.add_resource(Agent, "/agent")

    register_shared_dir(os.path.join(os.path.dirname(__file__), '../../../../data/shared'))
    clear_temp_dir()

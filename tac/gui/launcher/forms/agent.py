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

"""Implement the form for agent parameters."""

import wtforms
from wtforms import Form, StringField, IntegerField, FloatField, widgets, FileField


class AgentForm(Form):
    """The form to set the agent parameters."""

    name = StringField("Agent name", default="my_baseline_agent", validators=[wtforms.validators.Length(min=1)])
    agent_timeout = FloatField("Agent timeout", default=1.0, validators=[wtforms.validators.NumberRange(min=0.0)])
    max_reactions = IntegerField("Max reactions", default=100, widget=widgets.Input(input_type="number"), validators=[wtforms.validators.NumberRange(min=0.0)])
    register_as = wtforms.SelectField("Register as", choices=[("buyer", "buyer"), ("seller", "seller"), ("both", "both")], default="both")
    search_for = wtforms.SelectField("Search for", choices=[("buyers", "buyers"), ("sellers", "sellers"), ("both", "both")], default="both")
    is_world_modeling = wtforms.BooleanField("Is world modeling?", default=False)
    services_interval = IntegerField('Services interval', default=5, widget=widgets.Input(input_type="number"), validators=[wtforms.validators.NumberRange(min=2, message="At least two baseline agents.")],)
    pending_transaction_timeout = IntegerField("Pending transaction timeout", default=30, validators=[wtforms.validators.NumberRange(min=0.0)])
    private_key_pem = FileField("Private key PEM file path", default=None, validators=[wtforms.validators.Optional])
    rejoin = wtforms.BooleanField("Is rejoining?", default=False)


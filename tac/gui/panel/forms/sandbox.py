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

"""Implement the form for sandbox parameters."""

# from datetime import datetime
import wtforms
from wtforms import Form, IntegerField, FileField, widgets, FloatField  # , DateTimeField, StringField


class SandboxForm(Form):
    """The form to set the sandbox parameters."""

    nb_agents = IntegerField('No. Agents', default=5, widget=widgets.Input(input_type="number"), validators=[wtforms.validators.NumberRange(min=2, message="At least two agents.")])
    nb_goods = IntegerField('No. Goods', default=5, widget=widgets.Input(input_type="number"), validators=[wtforms.validators.NumberRange(min=2, message="At least two goods.")],)
    nb_baseline_agents = IntegerField('No. Baseline Agents', default=5, widget=widgets.Input(input_type="number"), validators=[wtforms.validators.NumberRange(min=2, message="At least two baseline agents.")],)
    services_interval = IntegerField('Services interval', default=5, widget=widgets.Input(input_type="number"), validators=[wtforms.validators.NumberRange(min=2, message="At least two baseline agents.")],)
    # data_output_dir = FileField("Data output directory", default="./data")
    # experiment_id = StringField("Experiment ID", [wtforms.validators.Required()], default="exp_1")
    lower_bound_factor = IntegerField('Lower bound factor', default=0, widget=widgets.Input(input_type="number"), validators=[wtforms.validators.NumberRange(min=0, message="Must be non-negative")],)
    upper_bound_factor = IntegerField('Upper bound factor', default=0, widget=widgets.Input(input_type="number"), validators=[wtforms.validators.NumberRange(min=0, message="Must be non-negative")],)
    tx_fee = FloatField("Transaction fee", default=0.1, validators=[wtforms.validators.NumberRange(min=0, message="Must be non-negative")],)
    registration_timeout = IntegerField("Registration timeout", default=10, validators=[wtforms.validators.NumberRange(min=0, message="Must be non-negative")])
    inactivity_timeout = IntegerField("Inactivity timeout", default=60, validators=[wtforms.validators.NumberRange(min=0, message="Must be non-negative")])
    competition_timeout = IntegerField("Competition timeout", default=240, validators=[wtforms.validators.NumberRange(min=0, message="Must be non-negative")])
    # start_time = DateTimeField("Start time", id='datepick', validators=[wtforms.validators.Required()])
    seed = IntegerField("Seed", default=42)
    whitelist_file = FileField("Whitelist file", default=None, validators=[wtforms.validators.Optional])

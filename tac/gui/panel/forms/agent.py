# -*- coding: utf-8 -*-

import wtforms
from wtforms import Form, StringField, IntegerField, FloatField, widgets, FileField

from tac.gui.panel.forms import ServicesIntervalField


class AgentForm(Form):
    name = StringField("Agent name", default="my_baseline_agent", validators=[wtforms.validators.Length(min=1)])
    agent_timeout = FloatField("Agent timeout", default=1.0, widget=widgets.Input(input_type="number"), validators=[wtforms.validators.NumberRange(min=0.0)])
    max_reactions = IntegerField("Max reactions", default=100, widget=widgets.Input(input_type="number"), validators=[wtforms.validators.NumberRange(min=0.0)])
    register_as = wtforms.SelectField("Register as", choices=[("buyer", "buyer"), ("seller", "seller"), ("both", "both")], default="both")
    search_for = wtforms.SelectField("Search for", choices=[("buyers", "buyers"), ("sellers", "sellers"), ("both", "both")], default="both")
    is_world_modeling = wtforms.BooleanField("Is world modeling?", default=False)
    services_interval = ServicesIntervalField()
    pending_transaction_timeout = IntegerField("Pending transaction timeout", default=30, validators=[wtforms.validators.NumberRange(min=0.0)])
    private_key_pem = whitelist_file = FileField("Private key PEM file path", default=None, validators=[wtforms.validators.Optional])
    rejoin = wtforms.BooleanField("Is rejoining?", default=False)

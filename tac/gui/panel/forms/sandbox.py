# -*- coding: utf-8 -*-

import wtforms
from wtforms import Form, StringField, IntegerField, FileField, DateTimeField

from tac.gui.panel.forms.custom_fields import NbAgentsField, NbGoodsField, NbBaselineAgentsField, ServicesIntervalField, \
    LowerBoundFactorField, UpperBoundFactorField, TxFeeField


class SandboxForm(Form):
    nb_agents = NbAgentsField()
    nb_goods = NbGoodsField()
    nb_baseline_agents = NbBaselineAgentsField()
    services_interval = ServicesIntervalField()
    data_output_dir = FileField("Data output directory", default="./data")
    experiment_id = StringField("Experiment ID", "experiment")
    lower_bound_factor = LowerBoundFactorField()
    upper_bound_factor = UpperBoundFactorField()
    tx_fee = TxFeeField()
    registration_timeout = IntegerField("Registration timeout", default=10, validators=[wtforms.validators.NumberRange(min=0, message="Must be non-negative")])
    inactivity_timeout = IntegerField("Inactivity timeout", default=60, validators=[wtforms.validators.NumberRange(min=0, message="Must be non-negative")])
    competition_timeout = IntegerField("Competition timeout", default=240, validators=[wtforms.validators.NumberRange(min=0, message="Must be non-negative")])
    start_time = DateTimeField("Start time")
    seed = IntegerField("Seed", default=42)
    whitelist_file = FileField("Whitelist file", default=None, validators=[wtforms.validators.Optional])

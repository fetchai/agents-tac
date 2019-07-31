# -*- coding: utf-8 -*-

import wtforms
from wtforms import Form, StringField, IntegerField, FloatField, widgets, FileField, DateTimeField


class NbAgentsField(IntegerField):

    def __init__(self, **kwargs):
        super().__init__(
            'No. Agents',
            default=5,
            widget=widgets.Input(input_type="number"),
            validators=[wtforms.validators.NumberRange(min=2, message="At least two agents.")],
            **kwargs
        )


class NbGoodsField(IntegerField):

    def __init__(self, **kwargs):
        super().__init__(
            'No. Goods',
            default=5,
            widget=widgets.Input(input_type="number"),
            validators=[wtforms.validators.NumberRange(min=2, message="At least two goods.")],
            **kwargs
        )


class NbBaselineAgentsField(IntegerField):

    def __init__(self, **kwargs):
        super().__init__(
            'No. Baseline Agents',
            default=5,
            widget=widgets.Input(input_type="number"),
            validators=[wtforms.validators.NumberRange(min=2, message="At least two baseline agents.")],
            **kwargs
        )


class ServicesIntervalField(IntegerField):

    def __init__(self, **kwargs):
        super().__init__(
            'Services interval',
            default=5,
            widget=widgets.Input(input_type="number"),
            validators=[wtforms.validators.NumberRange(min=2, message="At least two baseline agents.")],
            **kwargs
        )


class LowerBoundFactorField(IntegerField):

    def __init__(self, **kwargs):
        super().__init__(
            'Lower bound factor',
            default=0,
            widget=widgets.Input(input_type="number"),
            validators=[wtforms.validators.NumberRange(min=0, message="Must be non-negative")],
            **kwargs
        )


class UpperBoundFactorField(IntegerField):

    def __init__(self, **kwargs):
        super().__init__(
            'Upper bound factor',
            default=0,
            widget=widgets.Input(input_type="number"),
            validators=[wtforms.validators.NumberRange(min=0, message="Must be non-negative")],
            **kwargs
        )


class TxFeeField(FloatField):

    def __init__(self, **kwargs):

        super().__init__(
            "Transaction fee",
            default=0.1,
            widget=widgets.Input(input_type="number"),
            validators=[wtforms.validators.NumberRange(min=0, message="Must be non-negative")],
            **kwargs
        )


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

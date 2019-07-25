# -*- coding: utf-8 -*-
import wtforms
from wtforms import Form, StringField, IntegerField, FloatField, widgets, FileField


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


class OefIPAddress(StringField):

    def __init__(self, **kwargs):
        super().__init__(
            'OEF node IP address',
            validators=[wtforms.validators.IPAddress()],
            default="127.0.0.1",
            **kwargs
        )


class OefPort(IntegerField):

    def __init__(self, **kwargs):
        super().__init__(
            'OEF node port',
            default=10000,
            widget=widgets.Input(input_type="number"),
            validators=[wtforms.validators.NumberRange(min=1024, max=65535)],
            **kwargs
        )


class SandboxForm(Form):
    nb_agents = NbAgentsField()
    nb_goods = NbGoodsField()
    nb_baseline_agents = NbBaselineAgentsField()
    services_interval = ServicesIntervalField()
    oef_addr = OefIPAddress()
    oef_port = OefPort()
    data_output_dir = FileField("Data output directory")
    experiment_id = StringField("Experiment ID")
    lower_bound_factor = IntegerField("Lower bound factor", validators=[wtforms.validators.NumberRange(min=0)])
    upper_bound_factor = IntegerField("Upper bound factor", validators=[wtforms.validators.NumberRange(min=0)])
    tx_fee = FloatField("Transaction fee", validators=[wtforms.validators.NumberRange(min=0)])
    registration_timeout = IntegerField("Registration timeout")
    inactivity_timeout = IntegerField("Inactivity timeout")
    competition_timeout = IntegerField("Competition timeout")
    seed = IntegerField("Registration timeout")
    whitelist = FileField("Whitelist file", validators=[wtforms.validators.Optional])

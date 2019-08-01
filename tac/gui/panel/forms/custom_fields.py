import wtforms
from wtforms import IntegerField, widgets, FloatField


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

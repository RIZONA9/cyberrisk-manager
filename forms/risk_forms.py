from flask_wtf import FlaskForm
from wtforms import DateTimeLocalField, IntegerField
from wtforms.validators import InputRequired, NumberRange

from forms import text_field


class InitialRiskForm(FlaskForm):
    likelihood = IntegerField("Likelihood", validators=[InputRequired(), NumberRange(1, 5)])
    impact = IntegerField("Impact", validators=[InputRequired(), NumberRange(1, 5)])


class ResidualRiskForm(InitialRiskForm):
    mitigation_actions = text_field("Mitigation actions", 5000, multiline=True)
    control_description = text_field("Control description", 5000, multiline=True)
    mitigation_at = DateTimeLocalField("Mitigation time (UTC)", validators=[InputRequired()])
    responsible_person = text_field("Responsible person", 120)
    notes = text_field("Notes", 5000, required=False, multiline=True)

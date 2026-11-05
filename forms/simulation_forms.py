from flask_wtf import FlaskForm
from wtforms import HiddenField, SelectField
from wtforms.validators import InputRequired, Regexp

from forms import SCENARIOS


class SimulationForm(FlaskForm):
    scenario = SelectField("Scenario", choices=SCENARIOS, validators=[InputRequired()])
    request_key = HiddenField(validators=[InputRequired(), Regexp(r"\A[0-9a-f]{32}\Z")])

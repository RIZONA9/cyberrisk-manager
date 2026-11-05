from flask_wtf import FlaskForm
from wtforms import DateTimeLocalField, SelectField
from wtforms.validators import InputRequired

from forms import text_field
from models.response import RESPONSE_STAGES


class ResponseForm(FlaskForm):
    stage = SelectField("Response stage", choices=RESPONSE_STAGES, validators=[InputRequired()])
    description = text_field("Action description", 5000, multiline=True)
    responsible_person = text_field("Responsible person", 120)
    action_at = DateTimeLocalField("Action time (UTC)", validators=[InputRequired()])
    notes = text_field("Notes", 5000, required=False, multiline=True)

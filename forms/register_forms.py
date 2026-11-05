from flask_wtf import FlaskForm
from wtforms import DateField, SelectField
from wtforms.validators import InputRequired

from forms import text_field
from models.risk_register import RISK_STATUSES


class RegisterForm(FlaskForm):
    owner = text_field("Risk owner", 120)
    review_date = DateField("Review date", validators=[InputRequired()])
    status = SelectField("Risk status", choices=RISK_STATUSES, validators=[InputRequired()])

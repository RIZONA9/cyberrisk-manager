from flask_wtf import FlaskForm
from wtforms import BooleanField, SelectField
from wtforms.validators import InputRequired, Regexp

from forms import LEVELS, text_field


class AssetForm(FlaskForm):
    identifier = text_field("Identifier / hostname", 120)
    name = text_field("Display name", 200)
    category = SelectField("Asset type", choices=("Endpoint", "Server", "Account", "Application", "Network", "Data", "Other"), validators=[InputRequired()])
    owner = text_field("Asset owner", 120)
    criticality = SelectField("Business criticality", choices=LEVELS, validators=[InputRequired()])
    environment = SelectField("Environment", choices=("Production", "Test", "Lab", "Other"), validators=[InputRequired()])
    internet_exposed = BooleanField("Internet exposed")
    notes = text_field("Notes", 5000, required=False, multiline=True)

    def validate_identifier(self, field):
        Regexp(r"[a-zA-Z0-9][a-zA-Z0-9_.@-]*\Z", message="Use a hostname or asset identifier.")(self, field)

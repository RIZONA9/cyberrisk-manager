from wtforms import StringField, TextAreaField
from wtforms.validators import InputRequired, Length, Optional


LEVELS = ("Low", "Medium", "High", "Critical")
INCIDENT_STATUSES = ("Open", "In Progress", "Closed")
SCENARIOS = ("Phishing Attack", "Malware Infection", "Unauthorized Access", "Data Breach")


def clean_text(value):
    return value.strip() if value else ""


def text_field(label, limit, *, required=True, multiline=False, render_kw=None):
    field = TextAreaField if multiline else StringField
    return field(
        label,
        filters=[clean_text],
        validators=[InputRequired() if required else Optional(), Length(min=1, max=limit)],
        render_kw=render_kw,
    )

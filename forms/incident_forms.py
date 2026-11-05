from flask_wtf import FlaskForm
from wtforms import DateTimeLocalField, SelectField
from wtforms.validators import InputRequired, Optional

from forms import INCIDENT_STATUSES, LEVELS, text_field


class IncidentForm(FlaskForm):
    title = text_field("Title", 200)
    description = text_field("Description", 5000, multiline=True)
    incident_type = text_field("Incident type", 80)
    severity = SelectField("Severity", choices=LEVELS, validators=[InputRequired()])
    status = SelectField("Status", choices=INCIDENT_STATUSES, validators=[InputRequired()])
    detected_at = DateTimeLocalField("Detection date and time (UTC)", validators=[InputRequired()])
    first_observed_at = DateTimeLocalField("First observed activity (UTC)", validators=[Optional()])
    reported_by = text_field("Reported by", 120)
    asset_id = SelectField("Registered asset", coerce=int, default=0, validators=[Optional()])
    affected_asset = text_field("Affected asset (if unregistered)", 200, required=False)
    assigned_to = text_field("Assigned to", 120, required=False)
    resolution_notes = text_field("Resolution notes", 5000, required=False, multiline=True)

    def validate(self, extra_validators=None):
        valid = super().validate(extra_validators)
        if self.first_observed_at.data and self.detected_at.data and self.first_observed_at.data > self.detected_at.data:
            self.first_observed_at.errors.append("First observed activity must be at or before detection.")
            valid = False
        if not self.asset_id.data and not self.affected_asset.data:
            self.affected_asset.errors.append("Select a registered asset or enter its name.")
            return False
        return valid

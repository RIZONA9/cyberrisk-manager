from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from sqlalchemy import select, update

from extensions import db
from forms import text_field
from models import Alert, Asset, Incident, IncidentHistory
from modules.access import audit, editor_required
from modules.alert_import import ALERT_FILE_LIMIT, import_alerts, read_alerts, severity_for_level


bp = Blueprint("alerts", __name__, url_prefix="/alerts")


class AlertImportForm(FlaskForm):
    source = text_field("Wazuh source name", 80)
    upload = FileField("Wazuh JSON file", validators=[FileRequired()])


@bp.get("/")
@login_required
def index():
    scope = request.args.get("scope", "")
    statement = select(Alert)
    if scope == "pending":
        statement = statement.where(Alert.incident_id.is_(None))
    if scope == "linked":
        statement = statement.where(Alert.incident_id.is_not(None))
    page = db.paginate(statement.order_by(Alert.occurred_at.desc(), Alert.id.desc()),
                       per_page=20, max_per_page=20)
    return render_template("alerts.html", page=page, scope=scope)


@bp.route("/import", methods=["GET", "POST"])
@editor_required
def upload():
    form = AlertImportForm(source="wazuh-lab")
    if form.validate_on_submit():
        try:
            records = read_alerts(form.upload.data.stream.read(ALERT_FILE_LIMIT + 1))
        except ValueError as error:
            form.upload.errors.append(str(error))
        else:
            added, duplicates = import_alerts(form.source.data, records)
            audit("Imported alerts", "Wazuh batch", after=f"{added} new, {duplicates} duplicate")
            db.session.commit()
            flash(f"Imported {added} alerts. Skipped {duplicates} duplicates.", "success")
            return redirect(url_for("alerts.index"))
    return render_template("workspace_form.html", form=form, heading="Import Wazuh alerts",
                           label="ALERT TRIAGE", submit="Import alerts", back=url_for("alerts.index"),
                           multipart=True, description="Upload UTF-8 JSON or JSON Lines, up to 250 alerts and 128 KiB. Use a distinct source name per Wazuh manager.")


@bp.get("/<int:alert_id>")
@login_required
def detail(alert_id):
    return render_template("alert_detail.html", alert=db.get_or_404(Alert, alert_id))


@bp.post("/<int:alert_id>/convert")
@editor_required
def convert(alert_id):
    alert = db.get_or_404(Alert, alert_id)
    if alert.incident_id:
        return redirect(url_for("incidents.detail", incident_id=alert.incident_id))
    asset = alert.asset or db.session.scalar(
        select(Asset).where(Asset.identifier == alert.agent_name.lower())
    )
    incident = Incident(
        title=alert.description[:200], description=alert.description,
        incident_type="Imported security alert", severity=severity_for_level(alert.level),
        status="Open", detected_at=alert.occurred_at, reported_by=f"Wazuh · {alert.source}",
        asset_id=asset.id if asset else None, affected_asset=asset.name if asset else alert.agent_name,
    )
    incident.history.append(IncidentHistory(
        event="Created from alert", actor=current_user.username,
        details=f"Wazuh {alert.source}, alert {alert.external_id}, rule {alert.rule_id}.",
    ))
    db.session.add(incident)
    db.session.flush()
    incident_id = incident.id
    updated = db.session.execute(
        update(Alert).where(Alert.id == alert_id, Alert.incident_id.is_(None))
        .values(incident_id=incident_id, asset_id=incident.asset_id)
    )
    if updated.rowcount == 1:
        audit("Converted alert", f"ALERT-{alert_id}", after=f"INC-{incident_id}")
        db.session.commit()
        flash("Incident created from the alert.", "success")
    else:
        db.session.rollback()
        incident_id = db.get_or_404(Alert, alert_id).incident_id
    return redirect(url_for("incidents.detail", incident_id=incident_id))

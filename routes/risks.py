from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from extensions import db
from forms.risk_forms import InitialRiskForm, ResidualRiskForm
from models import IncidentHistory, RiskAssessment
from models.risk_register import RiskRegisterEntry
from models.timestamps import utc_now
from modules.risk_engine import build_assessment
from modules.access import audit, editor_required
from routes.incidents import get_incident

bp = Blueprint("risks", __name__)


@bp.route("/incidents/<int:incident_id>/risk/<any(initial,residual):kind>", methods=["GET", "POST"])
@editor_required
def assess(incident_id, kind):
    incident = get_incident(incident_id)
    is_initial = kind == "initial"
    if is_initial and incident.initial_risk:
        abort(409, "An initial assessment already exists.")
    if not is_initial and not incident.initial_risk:
        abort(409, "Record an initial assessment first.")

    form = InitialRiskForm() if is_initial else ResidualRiskForm(mitigation_at=utc_now())
    if form.validate_on_submit():
        mitigation = {} if is_initial else {
            name: form[name].data or None for name in (
                "mitigation_actions", "control_description", "mitigation_at",
                "responsible_person", "notes",
            )
        }
        assessment = build_assessment(kind.title(), form.likelihood.data, form.impact.data, **mitigation)
        previous = incident.latest_residual_risk or incident.initial_risk
        audit("Recorded risk assessment", f"RISK-{incident.id}",
              before=f"{previous.score} {previous.level}" if previous else None,
              after=f"{assessment.score} {assessment.level}", reason=assessment.kind)
        changed = db.session.execute(update(RiskRegisterEntry).where(
            RiskRegisterEntry.incident_id == incident_id, RiskRegisterEntry.status == "Accepted",
        ).values(status="Monitoring"))
        if changed.rowcount:
            audit("Reopened accepted risk", f"RISK-{incident.id}", before="Accepted",
                  after="Monitoring", reason="A new assessment requires a new approval.")
        incident.assessments.append(assessment)
        incident.history.append(IncidentHistory(
            event="Risk assessed", actor=current_user.username,
            details=f"{assessment.kind} risk recorded at {assessment.score} ({assessment.level}).",
        ))
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            if is_initial and db.session.scalar(select(RiskAssessment.id).where(
                RiskAssessment.incident_id == incident_id, RiskAssessment.kind == "Initial",
            )):
                abort(409, "An initial assessment already exists.")
            raise
        flash(f"{assessment.kind} assessment recorded.", "success")
        return redirect(url_for("incidents.detail", incident_id=incident_id))
    return render_template("risk_assessment.html", form=form, incident=incident, kind=kind)

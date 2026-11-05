from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from extensions import db
from forms import text_field
from models.governance import AuditEvent, RiskAcceptance
from models.timestamps import utc_now
from modules.access import audit, editor_required, roles_required
from routes.incidents import get_incident

bp = Blueprint("governance", __name__, url_prefix="/governance")


class ReasonForm(FlaskForm):
    reason = text_field("Reason", 2000, multiline=True)


@bp.get("/")
@login_required
def index():
    query = select(RiskAcceptance).options(joinedload(RiskAcceptance.incident))
    if current_user.role == "analyst":
        query = query.where(RiskAcceptance.requested_by == current_user.id)
    page = db.paginate(query.order_by(RiskAcceptance.id.desc()), per_page=20, max_per_page=20)
    return render_template("governance.html", page=page)


@bp.route("/request/<int:incident_id>", methods=["GET", "POST"])
@editor_required
def request_acceptance(incident_id):
    incident = get_incident(incident_id)
    risk = incident.latest_residual_risk or incident.initial_risk
    if not risk or not incident.register_entry:
        abort(409, "Record a risk assessment and register owner before requesting acceptance.")
    if incident.register_entry.status == "Accepted":
        abort(409, "This risk is already accepted.")
    form = ReasonForm()
    if form.validate_on_submit():
        db.session.add(RiskAcceptance(incident_id=incident.id, assessment_id=risk.id,
                                     requested_by=current_user.id, reason=form.reason.data))
        audit("Requested risk acceptance", f"RISK-{incident.id}", after=f"{risk.score} {risk.level}",
              reason=form.reason.data)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            abort(409, "An acceptance request is already pending for this incident.")
        flash("Request sent for approval.", "success")
        return redirect(url_for("governance.index"))
    return render_template("workspace_form.html", form=form, label="RISK GOVERNANCE",
                           heading=f"Request acceptance for RISK-{incident.id}", submit="Submit request",
                           back=url_for("register.detail", incident_id=incident.id))


@bp.route("/<int:request_id>/<any(approve,reject):decision>", methods=["GET", "POST"])
@roles_required("admin")
def review(request_id, decision):
    item = db.get_or_404(RiskAcceptance, request_id)
    if item.status != "Pending" or item.requested_by == current_user.id:
        abort(409, "Review requires a pending request from a different account.")
    incident = item.incident
    current = incident.latest_residual_risk or incident.initial_risk
    if decision == "approve" and (incident.archived_at or current is None or current.id != item.assessment_id):
        abort(409, "The risk changed after submission. Reject this request and ask for a fresh review.")
    form = ReasonForm()
    if form.validate_on_submit():
        status = "Approved" if decision == "approve" else "Rejected"
        result = db.session.execute(update(RiskAcceptance).where(
            RiskAcceptance.id == request_id, RiskAcceptance.status == "Pending",
        ).values(status=status, reviewed_by=current_user.id, reviewed_at=utc_now(),
                 decision_reason=form.reason.data))
        if result.rowcount != 1:
            db.session.rollback()
            abort(409, "This request has already been reviewed.")
        if status == "Approved":
            db.session.expire(incident, ["assessments", "archived_at", "register_entry"])
            current = incident.latest_residual_risk or incident.initial_risk
            if incident.archived_at or current is None or current.id != item.assessment_id:
                db.session.rollback()
                abort(409, "The risk changed during review. Request a fresh approval.")
            incident.register_entry.status = "Accepted"
        audit(f"{status} risk acceptance", f"RISK-{item.incident_id}", before="Pending",
              after=status, reason=form.reason.data)
        db.session.commit()
        flash(f"Acceptance request {status.lower()}.", "success")
        return redirect(url_for("governance.index"))
    return render_template("workspace_form.html", form=form, label="RISK GOVERNANCE",
                           heading=f"{decision.title()} request {item.id}", description=item.reason,
                           submit="Confirm decision", back=url_for("governance.index"))


@bp.get("/audit")
@roles_required("admin", "reviewer")
def events():
    page = db.paginate(select(AuditEvent).order_by(AuditEvent.id.desc()), per_page=20, max_per_page=20)
    return render_template("audit.html", page=page)

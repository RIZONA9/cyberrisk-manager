from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_, select

from extensions import db
from forms import INCIDENT_STATUSES, LEVELS
from forms.incident_forms import IncidentForm
from models import Alert, Asset, Incident, IncidentHistory
from models.response import RESPONSE_STAGES
from models.timestamps import utc_now
from modules.access import audit, editor_required

bp = Blueprint("incidents", __name__, url_prefix="/incidents")
EDITABLE_FIELDS = (
    "title", "description", "incident_type", "severity", "status", "detected_at",
    "reported_by", "affected_asset", "assigned_to", "resolution_notes", "first_observed_at",
)


def incident_form(**kwargs):
    form = IncidentForm(**kwargs)
    assets = {asset.id: asset for asset in db.session.scalars(select(Asset).order_by(Asset.name))}
    form.asset_id.choices = [(0, "Unregistered asset")] + [
        (item.id, f"{item.name} ({item.identifier})") for item in assets.values()
    ]
    if form.asset_id.data is None:
        form.asset_id.data = 0
    return form, assets


def incident_values(form, assets):
    values = {name: form[name].data or None for name in EDITABLE_FIELDS}
    asset = assets.get(form.asset_id.data)
    if asset:
        values["affected_asset"] = asset.name
    return {**values, "asset_id": asset.id if asset else None}


def get_incident(incident_id):
    incident = db.get_or_404(Incident, incident_id)
    if incident.archived_at is not None:
        abort(404)
    return incident


@bp.get("/")
@login_required
def index():
    query = request.args.get("q", "").strip()[:200]
    severity = request.args.get("severity", "")
    status = request.args.get("status", "")
    archived = request.args.get("scope") == "archive"
    statement = select(Incident).where(
        Incident.archived_at.is_not(None) if archived else Incident.archived_at.is_(None)
    )
    if query:
        statement = statement.where(or_(
            Incident.title.icontains(query, autoescape=True),
            Incident.description.icontains(query, autoescape=True),
            Incident.affected_asset.icontains(query, autoescape=True),
            Incident.incident_type.icontains(query, autoescape=True),
        ))
    if severity in LEVELS:
        statement = statement.where(Incident.severity == severity)
    if status in INCIDENT_STATUSES:
        statement = statement.where(Incident.status == status)
    page = db.paginate(statement.order_by(Incident.detected_at.desc(), Incident.id.desc()),
                       per_page=20, max_per_page=20)
    return render_template("incidents.html", page=page, levels=LEVELS, statuses=INCIDENT_STATUSES,
                           q=query, severity=severity, status=status, archived=archived)


@bp.get("/<int:incident_id>")
@login_required
def detail(incident_id):
    incident = db.get_or_404(Incident, incident_id)
    alert = db.session.scalar(select(Alert).where(Alert.incident_id == incident_id))
    return render_template("incident_details.html", incident=incident, alert=alert, stages=RESPONSE_STAGES,
                           recorded_stages={action.stage for action in incident.response_actions})


@bp.route("/new", methods=["GET", "POST"])
@editor_required
def create():
    form, assets = incident_form(status="Open", detected_at=utc_now())
    if form.validate_on_submit():
        incident = Incident(**incident_values(form, assets))
        incident.history.append(IncidentHistory(
            event="Created", actor=current_user.username, details="Incident created.",
        ))
        db.session.add(incident)
        db.session.flush()
        audit("Created incident", f"INC-{incident.id}", after=incident.status)
        db.session.commit()
        flash("Incident created.", "success")
        return redirect(url_for("incidents.detail", incident_id=incident.id))
    return render_template("incident_form.html", form=form, heading="Create incident", incident=None)


@bp.route("/<int:incident_id>/edit", methods=["GET", "POST"])
@editor_required
def edit(incident_id):
    incident = get_incident(incident_id)
    form, assets = incident_form(obj=incident)
    if form.validate_on_submit():
        previous_status = incident.status
        changes = []
        for name, value in incident_values(form, assets).items():
            previous = getattr(incident, name)
            if previous != value:
                changes.append(
                    f"Status: {previous} → {value}" if name == "status" else form[name].label.text
                )
                setattr(incident, name, value)
        if changes:
            audit("Edited incident", f"INC-{incident.id}", before=previous_status,
                  after=incident.status, reason=", ".join(changes))
            incident.history.append(IncidentHistory(
                event="Edited", actor=current_user.username,
                details="Changed " + ", ".join(changes) + ".",
            ))
        db.session.commit()
        flash("Incident saved.", "success")
        return redirect(url_for("incidents.detail", incident_id=incident.id))
    return render_template("incident_form.html", form=form, heading="Edit incident", incident=incident)


@bp.route("/<int:incident_id>/delete", methods=["GET", "POST"])
@editor_required
def delete(incident_id):
    incident = get_incident(incident_id)
    if request.method == "POST":
        incident.archived_at = utc_now()
        audit("Archived incident", f"INC-{incident.id}", before=incident.status, after="Archived")
        incident.history.append(IncidentHistory(
            event="Archived", actor=current_user.username, details="Removed from active workspace.",
        ))
        db.session.commit()
        flash("Incident archived. Its history is retained.", "success")
        return redirect(url_for("incidents.index"))
    return render_template("incident_delete.html", incident=incident)

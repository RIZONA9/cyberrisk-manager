from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from extensions import db
from forms.response_forms import ResponseForm
from models import Incident, IncidentHistory, ResponseAction
from models.timestamps import utc_now
from modules.access import audit, editor_required
from routes.incidents import get_incident

bp = Blueprint("responses", __name__)


@bp.get("/response/")
@login_required
def index():
    page = db.paginate(
        select(ResponseAction).join(Incident).where(Incident.archived_at.is_(None))
        .options(joinedload(ResponseAction.incident))
        .order_by(ResponseAction.action_at.desc(), ResponseAction.id.desc()),
        per_page=20, max_per_page=20,
    )
    return render_template("responses.html", page=page)


@bp.route("/incidents/<int:incident_id>/response/new", methods=["GET", "POST"])
@editor_required
def add(incident_id):
    incident = get_incident(incident_id)
    form = ResponseForm(action_at=utc_now())
    if form.validate_on_submit():
        action = ResponseAction(**{
            key: form[key].data or None for key in (
                "stage", "description", "responsible_person", "action_at", "notes",
            )
        })
        incident.response_actions.append(action)
        audit("Recorded response action", f"INC-{incident.id}", after=action.stage)
        incident.history.append(IncidentHistory(
            event="Response recorded", actor=current_user.username, details=action.stage,
        ))
        db.session.commit()
        flash("Response action recorded.", "success")
        return redirect(url_for("incidents.detail", incident_id=incident.id, _anchor="response"))
    return render_template("response_form.html", incident=incident, form=form)

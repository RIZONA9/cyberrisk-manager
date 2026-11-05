from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import selectinload

from extensions import db
from forms import LEVELS
from forms.register_forms import RegisterForm
from models import Incident, RiskAssessment
from models.risk_register import RISK_STATUSES, RiskRegisterEntry
from modules.risk_queries import current_risk_id
from modules.access import audit
from routes.incidents import get_incident

bp = Blueprint("register", __name__, url_prefix="/risks")


@bp.get("/")
@login_required
def index():
    query = request.args.get("q", "").strip()[:200]
    level = request.args.get("level", "")
    status = request.args.get("status", "")
    sort = request.args.get("sort", "score")
    statement = (
        select(Incident).join(RiskAssessment, RiskAssessment.id == current_risk_id())
        .outerjoin(RiskRegisterEntry)
        .where(Incident.archived_at.is_(None))
        .options(selectinload(Incident.assessments), selectinload(Incident.register_entry))
    )
    if query:
        statement = statement.where(or_(
            Incident.title.icontains(query, autoescape=True),
            Incident.description.icontains(query, autoescape=True),
            RiskRegisterEntry.owner.icontains(query, autoescape=True),
        ))
    if level in LEVELS:
        statement = statement.where(RiskAssessment.level == level)
    if status in RISK_STATUSES:
        statement = statement.where(func.coalesce(RiskRegisterEntry.status, "Open") == status)
    order = {
        "score": RiskAssessment.score.desc(),
        "title": Incident.title.asc(),
        "review": RiskRegisterEntry.review_date.asc().nulls_last(),
    }
    page = db.paginate(statement.order_by(order.get(sort, order["score"]), Incident.id),
                       per_page=20, max_per_page=20)
    return render_template("risk_register.html", page=page, q=query, level=level, status=status,
                           sort=sort, levels=LEVELS, statuses=RISK_STATUSES)


@bp.route("/<int:incident_id>", methods=["GET", "POST"])
@login_required
def detail(incident_id):
    incident = get_incident(incident_id)
    if not incident.initial_risk:
        abort(404)
    form = RegisterForm(obj=incident.register_entry, status="Open")
    if request.method == "POST" and current_user.role not in ("admin", "analyst"):
        abort(403)
    if form.validate_on_submit():
        values = {key: form[key].data for key in ("owner", "review_date", "status")}
        previous = incident.register_entry.status if incident.register_entry else None
        if values["status"] == "Accepted" and previous != "Accepted":
            form.status.errors.append("Submit an acceptance request for approval.")
            return render_template("risk_register_detail.html", incident=incident, form=form)
        if values["status"] == "Accepted":
            result = db.session.execute(update(RiskRegisterEntry).where(
                RiskRegisterEntry.incident_id == incident_id, RiskRegisterEntry.status == "Accepted",
            ).values(**values))
            if result.rowcount != 1:
                db.session.rollback()
                abort(409, "The existing acceptance changed. Reload the register entry.")
        else:
            db.session.execute(
                insert(RiskRegisterEntry).values(incident_id=incident.id, **values)
                .on_conflict_do_update(index_elements=["incident_id"], set_=values)
            )
        audit("Updated risk register", f"RISK-{incident.id}", before=previous, after=values["status"])
        db.session.commit()
        flash("Risk register entry updated.", "success")
        return redirect(url_for("register.detail", incident_id=incident.id))
    return render_template("risk_register_detail.html", incident=incident, form=form)

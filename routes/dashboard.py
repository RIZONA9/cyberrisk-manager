from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func, select, union_all

from extensions import db
from forms import INCIDENT_STATUSES, LEVELS
from models import Incident, IncidentHistory, ResponseAction, RiskAssessment, Simulation
from modules.risk_queries import current_risk_id
from modules.response_metrics import CONTAINMENT_TARGET_HOURS, response_metrics

bp = Blueprint("dashboard", __name__)


@bp.get("/metrics/response")
@login_required
def metrics():
    return render_template("response_metrics.html", groups=response_metrics(),
                           targets=CONTAINMENT_TARGET_HOURS)


@bp.get("/")
@login_required
def index():
    active = Incident.archived_at.is_(None)
    statuses = dict(db.session.execute(
        select(Incident.status, func.count()).where(active).group_by(Incident.status)
    ).all())
    risks = dict(db.session.execute(
        select(RiskAssessment.level, func.count()).select_from(Incident)
        .join(RiskAssessment, RiskAssessment.id == current_risk_id())
        .where(active)
        .group_by(RiskAssessment.level)
    ).all())
    recent = db.session.scalars(
        select(Incident).where(active).order_by(Incident.created_at.desc(), Incident.id.desc()).limit(5)
    ).all()
    activity = union_all(
        select(Incident.title.label("label"), Incident.updated_at.label("at")).where(active),
        select(ResponseAction.description, ResponseAction.action_at).join(Incident).where(active),
        select(Simulation.scenario_type, Simulation.created_at),
        select(IncidentHistory.details, IncidentHistory.occurred_at),
    ).subquery()
    return render_template(
        "dashboard.html", recent=recent,
        activity=db.session.execute(select(activity).order_by(activity.c.at.desc()).limit(6)).all(),
        metrics={
            "Total incidents": sum(statuses.values()),
            "Open incidents": statuses.get("Open", 0) + statuses.get("In Progress", 0),
            "Closed incidents": statuses.get("Closed", 0),
            "Total simulations": db.session.scalar(select(func.count()).select_from(Simulation)),
        },
        chart={"risks": {key: risks.get(key, 0) for key in LEVELS},
               "statuses": {key: statuses.get(key, 0) for key in INCIDENT_STATUSES}},
    )

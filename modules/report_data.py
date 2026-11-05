from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from extensions import db
from forms import INCIDENT_STATUSES, LEVELS
from models import Incident, ResponseAction, RiskAssessment, Simulation, SimulationEvent
from modules.risk_queries import current_risk_id


@dataclass
class ReportSection:
    title: str
    headings: tuple[str, ...]
    rows: list[tuple]


def incidents_report():
    incidents = db.session.scalars(select(Incident).order_by(Incident.id))
    return [ReportSection("Incidents", (
        "ID", "Title", "Type", "Severity", "Status", "Detected UTC", "Asset", "Description",
    ), [
        (f"INC-{item.id}", item.title, item.incident_type, item.severity,
         "Archived" if item.archived_at else item.status,
         item.detected_at, item.affected_asset, item.description)
        for item in incidents
    ])]


def risk_assessments(kind):
    records = db.session.execute(
        select(RiskAssessment, Incident.title).join(Incident)
        .where(RiskAssessment.kind == kind)
        .order_by(RiskAssessment.incident_id, RiskAssessment.assessed_at, RiskAssessment.id)
    )
    rows = [
        (f"INC-{risk.incident_id}", title, risk.likelihood, risk.impact, risk.score,
         risk.level, risk.assessed_at, risk.mitigation_actions)
        for risk, title in records
    ]
    headings = (
        "Incident", "Title", "Likelihood", "Impact", "Score", "Level", "Assessed UTC", "Mitigation",
    )
    if kind == "Initial":
        headings = headings[:-1]
        rows = [row[:-1] for row in rows]
    return [ReportSection(f"{kind} assessments", headings, rows)]


def assessments_by_incident():
    return db.session.scalars(
        select(Incident)
        .where(Incident.archived_at.is_(None), Incident.assessments.any(RiskAssessment.kind == "Initial"))
        .options(selectinload(Incident.assessments), selectinload(Incident.register_entry))
        .order_by(Incident.id)
    )


def assessment_pair(incident):
    initial, residual = incident.initial_risk, incident.latest_residual_risk
    return (
        initial.score, initial.level,
        residual.score if residual else None, residual.level if residual else None,
    )


def comparison_report():
    rows = []
    for incident in assessments_by_incident():
        pair = assessment_pair(incident)
        rows.append((f"INC-{incident.id}", incident.title, *pair,
                     pair[2] - pair[0] if pair[2] is not None else None))
    return [ReportSection("Initial and residual risk", (
        "Incident", "Title", "Initial score", "Initial level", "Residual score", "Residual level", "Change",
    ), rows)]


def register_report():
    rows = []
    for incident in assessments_by_incident():
        entry = incident.register_entry
        residual = incident.latest_residual_risk
        rows.append((
            f"RISK-{incident.id}", f"INC-{incident.id}", incident.title, *assessment_pair(incident),
            entry.owner if entry else None, entry.review_date if entry else None,
            entry.status if entry else "Open", residual.mitigation_actions if residual else None,
        ))
    return [ReportSection("Risk register", (
        "Risk ID", "Incident", "Title", "Initial score", "Initial level", "Residual score",
        "Residual level", "Owner", "Review date", "Status", "Mitigation",
    ), rows)]


def simulations_report():
    runs = db.session.scalars(select(Simulation).order_by(Simulation.id))
    events = db.session.scalars(
        select(SimulationEvent).order_by(SimulationEvent.simulation_id,
                                        SimulationEvent.occurred_at, SimulationEvent.id)
    )
    return [
        ReportSection("Simulation runs", (
            "Run", "Scenario", "Incident", "Status", "Start UTC", "End UTC", "Result",
        ), [
            (f"SIM-{run.id}", run.scenario_type, f"INC-{run.incident_id}" if run.incident_id else None,
             run.status, run.started_at, run.ended_at, run.result_summary)
            for run in runs
        ]),
        ReportSection("Simulation events", (
            "Run", "Event", "Description", "Time UTC", "Status",
        ), [
            (f"SIM-{event.simulation_id}", event.event_type, event.description,
             event.occurred_at, event.status)
            for event in events
        ]),
    ]


def response_report():
    actions = db.session.execute(
        select(ResponseAction, Incident.title).join(Incident)
        .order_by(ResponseAction.incident_id, ResponseAction.action_at, ResponseAction.id)
    )
    return [ReportSection("Response actions", (
        "Incident", "Title", "Stage", "Action", "Responsible person", "Time UTC", "Notes",
    ), [
        (f"INC-{action.incident_id}", title, action.stage, action.description,
         action.responsible_person, action.action_at, action.notes)
        for action, title in actions
    ])]


def summary_report():
    statuses = dict(db.session.execute(
        select(Incident.status, func.count()).where(Incident.archived_at.is_(None))
        .group_by(Incident.status)
    ).all())
    levels = dict(db.session.execute(
        select(RiskAssessment.level, func.count()).select_from(Incident)
        .join(RiskAssessment, RiskAssessment.id == current_risk_id())
        .where(Incident.archived_at.is_(None)).group_by(RiskAssessment.level)
    ).all())
    rows = [
        ("Total active-workspace incidents", sum(statuses.values())),
        *((f"{status} incidents", statuses.get(status, 0)) for status in INCIDENT_STATUSES),
        *((f"{level} current risks", levels.get(level, 0)) for level in LEVELS),
        ("Simulations", db.session.scalar(select(func.count()).select_from(Simulation))),
        ("Response actions", db.session.scalar(select(func.count()).select_from(ResponseAction))),
    ]
    return [ReportSection("Security metrics", ("Metric", "Count"), rows)]


REPORTS = {
    "incidents": ("Incident report", incidents_report),
    "initial-risk": ("Initial risk report", lambda: risk_assessments("Initial")),
    "residual-risk": ("Residual risk report", lambda: risk_assessments("Residual")),
    "risk-comparison": ("Initial vs. residual risk comparison", comparison_report),
    "risk-register": ("Risk register report", register_report),
    "simulations": ("Simulation report", simulations_report),
    "responses": ("Incident response report", response_report),
    "summary": ("Overall security summary", summary_report),
}

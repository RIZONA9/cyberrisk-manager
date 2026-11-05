from statistics import median

from sqlalchemy import case, func, select

from extensions import db
from models import Alert, Incident, ResponseAction, Simulation
from models.timestamps import utc_now


CONTAINMENT_TARGET_HOURS = {"Critical": 4, "High": 24, "Medium": 72, "Low": 168}


def elapsed_hours(start, end):
    if start is not None and end is not None and end >= start:
        return (end - start).total_seconds() / 3600
    return None


def summarize(records, now):
    durations = {"Detection": [], "Containment": [], "Recovery": []}
    overdue = 0
    breached = 0
    for record in records:
        points = (
            ("Detection", record.first_observed_at, record.detected_at),
            ("Containment", record.detected_at, record.contained_at),
            ("Recovery", record.detected_at, record.recovered_at),
        )
        for label, start, end in points:
            hours = elapsed_hours(start, end)
            if hours is not None:
                durations[label].append(hours)
        target = CONTAINMENT_TARGET_HOURS[record.severity]
        contained_hours = elapsed_hours(record.detected_at, record.contained_at)
        if contained_hours is not None:
            breached += contained_hours > target
        elif record.status != "Closed":
            age = elapsed_hours(record.detected_at, now)
            overdue += age is not None and age > target
    return {
        "total": len(records), "overdue": overdue, "breached": breached,
        "durations": [
            (label, median(values) if values else None, len(values))
            for label, values in durations.items()
        ],
    }


def response_metrics(now=None):
    simulated = select(Simulation.id).where(Simulation.incident_id == Incident.id).exists()
    imported = select(Alert.id).where(Alert.incident_id == Incident.id).exists()
    origin = case(
        (simulated, "Simulation"), (Incident.demo_key.is_not(None), "Demo"),
        (imported, "Imported"), else_="Manual",
    )
    statement = (
        select(
            origin.label("origin"), Incident.status, Incident.severity, Incident.first_observed_at,
            Incident.detected_at,
            func.min(case((ResponseAction.stage == "Containment", ResponseAction.action_at),
                          else_=None)).label("contained_at"),
            func.min(case((ResponseAction.stage == "Recovery", ResponseAction.action_at),
                          else_=None)).label("recovered_at"),
        )
        .outerjoin(ResponseAction)
        .where(Incident.archived_at.is_(None))
        .group_by(Incident.id)
    )
    groups = {label: [] for label in ("Manual", "Imported", "Simulation", "Demo")}
    for record in db.session.execute(statement):
        groups[record.origin].append(record)
    now = now or utc_now()
    return {label: summarize(records, now) for label, records in groups.items()}

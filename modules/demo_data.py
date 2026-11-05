from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import click
from flask import current_app
from flask.cli import with_appcontext
from flask_migrate import upgrade
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from werkzeug.security import generate_password_hash

from extensions import db
from models import Incident, IncidentHistory, ResponseAction, Simulation, User
from models.risk_register import RiskRegisterEntry
from models.timestamps import utc_now
from modules.risk_engine import build_assessment
from modules.scenarios import SCENARIO_DETAILS
from modules.simulation_engine import populate_run


DEMO_USERNAME = "admin"
DEMO_PASSWORD = "Admin@12345"
MIGRATIONS = Path(__file__).resolve().parents[1] / "migrations"


@dataclass(frozen=True)
class DemoIncident:
    key: str
    title: str
    description: str
    category: str
    asset: str
    status: str
    initial: tuple[int, int]
    residual: tuple[int, int]
    mitigation: str


SAMPLE_INCIDENTS = (
    DemoIncident(
        "unexpected-access-grant", "Unexpected access grant",
        "An audit flagged an inherited permission on a training service account.",
        "Unauthorized Access", "Training identity directory", "Open",
        (4, 4), (3, 4), "Limited the training account to approved resource groups.",
    ),
    DemoIncident(
        "quarantine-queue", "Quarantine queue review",
        "The training mail gateway flagged several messages with unexpected attachments.",
        "Phishing Attack", "Training mail gateway", "In Progress",
        (3, 3), (1, 3), "Applied the updated attachment policy to the training queue.",
    ),
    DemoIncident(
        "unexpected-export", "Unexpected export volume",
        "A synthetic audit trail flagged a bulk export outside the planned exercise window.",
        "Data Breach", "Sample analytics store", "Open",
        (5, 5), (4, 5), "Limited export permissions to designated training accounts.",
    ),
)


def seed_incidents(now):
    created = 0
    for index, sample in enumerate(SAMPLE_INCIDENTS, start=1):
        detected = now - timedelta(days=index)
        initial = build_assessment("Initial", *sample.initial, assessed_at=detected)
        result = db.session.execute(insert(Incident).values(
            demo_key=sample.key, title=sample.title, description=sample.description,
            incident_type=sample.category, affected_asset=sample.asset, status=sample.status,
            severity=initial.level, detected_at=detected, reported_by="Demo service desk",
            assigned_to="Training analyst", created_at=detected, updated_at=detected,
        ).on_conflict_do_nothing(index_elements=["demo_key"]))
        if not result.rowcount:
            continue
        incident = db.session.scalar(select(Incident).where(Incident.demo_key == sample.key))
        incident.assessments.extend([
            initial,
            build_assessment(
                "Residual", *sample.residual, assessed_at=detected + timedelta(hours=2),
                mitigation_actions=sample.mitigation, control_description=sample.mitigation,
                mitigation_at=detected + timedelta(hours=1), responsible_person="Training analyst",
                notes="Sample data for the local academic demonstration.",
            ),
        ])
        incident.response_actions.append(ResponseAction(
            stage="Containment", description=sample.mitigation,
            responsible_person="Training analyst", action_at=detected + timedelta(hours=1),
            notes="Synthetic demo record.",
        ))
        incident.history.append(IncidentHistory(
            event="Created", actor="Demo initializer", details="Sample incident added.",
            occurred_at=detected,
        ))
        incident.register_entry = RiskRegisterEntry(
            owner="Training analyst", status="Monitoring", review_date=now.date() + timedelta(days=14),
        )
        created += 1
    return created


def seed_simulations(now):
    created = 0
    for scenario in SCENARIO_DETAILS:
        key = uuid5(NAMESPACE_URL, f"cyberrisk-manager/demo/v1/{scenario}").hex
        result = db.session.execute(insert(Simulation).values(
            scenario_type=scenario, request_key=key, status="Completed",
            started_at=now, created_at=now,
        ).on_conflict_do_nothing(index_elements=["request_key"]))
        if not result.rowcount:
            continue
        simulation = db.session.scalar(select(Simulation).where(Simulation.request_key == key))
        populate_run(simulation, "Demo initializer")
        created += 1
    return created


@click.command("seed-demo")
@with_appcontext
def seed_demo():
    """Apply migrations and add local academic demonstration data."""
    if not current_app.config["ALLOW_DEMO_DATA"]:
        raise click.ClickException("Demo data is enabled only for local development and tests.")
    upgrade(directory=str(MIGRATIONS))
    now = utc_now()
    try:
        exists = db.session.scalar(select(User.id).where(User.username == DEMO_USERNAME))
        if exists is None:
            db.session.execute(insert(User).values(
                username=DEMO_USERNAME, role="admin", password_hash=generate_password_hash(DEMO_PASSWORD),
                created_at=now,
            ).on_conflict_do_nothing(index_elements=["username"]))
        incidents = seed_incidents(now)
        simulations = seed_simulations(now)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    click.echo(f"Demo data ready. Added {incidents} sample incidents and {simulations} simulations.")

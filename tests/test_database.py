from pathlib import Path

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from app import create_app
from config import TestingConfig
from extensions import db
from models import Incident, ResponseAction, RiskAssessment, Simulation, SimulationEvent, User
from models.timestamps import utc_now


CORE_TABLES = {
    "incidents", "response_actions", "risk_assessments", "simulations",
    "simulation_events", "users", "incident_history", "risk_register_entries", "assets", "alerts",
    "audit_events", "risk_acceptances", "vulnerabilities", "exercise_runs", "exercise_decisions",
}
MIGRATIONS_DIRECTORY = Path(__file__).resolve().parents[1] / "migrations"


def run_migration(app, command, *args):
    result = app.test_cli_runner().invoke(
        args=["db", command, "--directory", str(MIGRATIONS_DIRECTORY), *args]
    )
    assert result.exit_code == 0, f"{result.output}\n{result.exception!r}"


@pytest.fixture
def migrated_app(tmp_path):
    class FileTestingConfig(TestingConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{(tmp_path / 'test.db').as_posix()}"

    app = create_app(FileTestingConfig)
    run_migration(app, "upgrade")
    yield app
    with app.app_context():
        db.engine.dispose()


def make_incident():
    return Incident(
        title="Suspicious email",
        description="An employee reported an unexpected sign-in link.",
        incident_type="Phishing Attack",
        severity="High",
        detected_at=utc_now(),
        reported_by="Service Desk",
        affected_asset="Employee mailbox",
    )


def test_migration_creates_expected_schema_and_rolls_back(migrated_app):
    with migrated_app.app_context():
        assert set(inspect(db.engine).get_table_names()) == CORE_TABLES | {"alembic_version"}

    run_migration(migrated_app, "check")
    run_migration(migrated_app, "downgrade", "base")
    with migrated_app.app_context():
        assert CORE_TABLES.isdisjoint(inspect(db.engine).get_table_names())

    run_migration(migrated_app, "upgrade")
    with migrated_app.app_context():
        assert set(inspect(db.engine).get_table_names()) == CORE_TABLES | {"alembic_version"}


def test_models_and_assessment_history_persist(migrated_app):
    with migrated_app.app_context():
        incident = make_incident()
        user = User(username="analyst", password_hash=generate_password_hash("test-password"))
        initial = RiskAssessment(
            kind="Initial", likelihood=4, impact=5, score=20, level="Critical"
        )
        first_residual = RiskAssessment(
            kind="Residual", likelihood=2, impact=3, score=6, level="Medium",
            mitigation_actions="Revoked exposed sessions",
            control_description="Invalidate active session tokens.",
            mitigation_at=utc_now(), responsible_person="Security Analyst",
            notes="Confirmed reauthentication.",
        )
        action = ResponseAction(
            stage="Containment", description="Simulated session revocation.",
            responsible_person="Security Analyst",
        )
        simulation = Simulation(scenario_type="Phishing Attack", incident=incident)
        simulation.events.append(
            SimulationEvent(
                event_type="Detection", description="Simulated phishing report.",
                status="Recorded",
            )
        )
        incident.assessments.extend([initial, first_residual])
        incident.response_actions.append(action)
        db.session.add_all([user, incident])
        db.session.commit()
        user_id, incident_id = user.id, incident.id

        incident.assessments.append(
            RiskAssessment(kind="Residual", likelihood=1, impact=3, score=3, level="Low")
        )
        incident.status = "Closed"
        db.session.commit()

    # Disposing the pool ensures the next app context reconnects to the file.
    with migrated_app.app_context():
        db.engine.dispose()
        incident = db.session.get(Incident, incident_id)
        user = db.session.get(User, user_id)
        assert user.username == "analyst"
        assert user.password_hash != "test-password"
        assert user.created_at is not None
        assert incident.status == "Closed"
        assert [
            (item.kind, item.likelihood, item.impact, item.score, item.level)
            for item in incident.assessments
        ] == [
            ("Initial", 4, 5, 20, "Critical"),
            ("Residual", 2, 3, 6, "Medium"),
            ("Residual", 1, 3, 3, "Low"),
        ]
        assert incident.assessments[1].mitigation_actions == "Revoked exposed sessions"
        assert incident.assessments[1].mitigation_at is not None
        assert incident.response_actions[0].incident is incident
        assert incident.response_actions[0].stage == "Containment"
        simulation = incident.simulations[0]
        assert simulation.status == "Pending"
        assert simulation.incident is incident
        assert simulation.events[0].event_type == "Detection"
        assert simulation.events[0].simulation is simulation


def test_duplicate_initial_assessment_is_rejected(migrated_app):
    with migrated_app.app_context():
        incident = make_incident()
        db.session.add(incident)
        incident.assessments.append(
            RiskAssessment(kind="Initial", likelihood=4, impact=5, score=20, level="Critical")
        )
        db.session.commit()
        incident.assessments.append(
            RiskAssessment(kind="Initial", likelihood=3, impact=4, score=12, level="High")
        )
        with pytest.raises(IntegrityError, match="UNIQUE constraint failed"):
            db.session.commit()
        db.session.rollback()
        assert [item.score for item in incident.assessments] == [20]


@pytest.mark.parametrize(("likelihood", "impact"), [(0, 3), (2, 6), (2.5, 3)])
def test_invalid_assessment_inputs_are_rejected(migrated_app, likelihood, impact):
    with migrated_app.app_context():
        db.session.add(
            RiskAssessment(
                incident=make_incident(), kind="Initial", likelihood=likelihood,
                impact=impact, score=6, level="Medium",
            )
        )
        with pytest.raises(IntegrityError, match="CHECK constraint failed"):
            db.session.commit()
        db.session.rollback()


def test_foreign_keys_protect_history(migrated_app):
    with migrated_app.app_context():
        incident = make_incident()
        simulation = Simulation(scenario_type="Phishing Attack", incident=incident)
        simulation.events.append(
            SimulationEvent(event_type="Detection", description="Simulated alert.", status="Recorded")
        )
        db.session.add(incident)
        db.session.commit()

        for parent in (incident, simulation):
            db.session.delete(parent)
            with pytest.raises(IntegrityError, match="FOREIGN KEY constraint failed"):
                db.session.commit()
            db.session.rollback()

        db.session.add(
            SimulationEvent(
                simulation_id=simulation.id + 1,
                event_type="Detection", description="Orphan event.", status="Recorded",
            )
        )
        with pytest.raises(IntegrityError, match="FOREIGN KEY constraint failed"):
            db.session.commit()
        db.session.rollback()
        assert len(simulation.events) == 1

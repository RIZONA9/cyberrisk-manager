from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app import create_app
from config import TestingConfig
from conftest import csrf_token
from extensions import db
from models import Incident, Simulation
from models.response import RESPONSE_STAGES
from models.timestamps import utc_now
from modules import simulation_engine
from modules.scenarios import SCENARIO_DETAILS
from modules.risk_engine import build_assessment


@pytest.mark.parametrize("scenario", list(SCENARIO_DETAILS))
def test_simulation_workflow_and_duplicate_request(app, signed_in, scenario):
    page = signed_in.get("/simulations/")
    assert SCENARIO_DETAILS[scenario].description.encode() in page.data
    payload = {"scenario": scenario, "request_key": uuid4().hex, "csrf_token": csrf_token(page)}
    first = signed_in.post("/simulations/", data=payload)
    assert first.status_code == 302
    assert signed_in.post("/simulations/", data=payload).location == first.location
    result = signed_in.get(first.location)
    assert b"Simulation report" in result.data and b"Completed" in result.data
    assert "Simulation ·".encode() in signed_in.get("/").data
    with app.app_context():
        simulation = db.session.scalars(select(Simulation)).one()
        assert simulation.status == "Completed"
        assert simulation.started_at <= simulation.ended_at
        assert db.session.scalar(select(func.count()).select_from(Incident)) == 1
        incident = simulation.incident
        assert incident.status == "Closed"
        assert incident.initial_risk.score > incident.latest_residual_risk.score > 0
        assert {action.stage for action in incident.response_actions} == set(RESPONSE_STAGES)
        assert all(action.description.startswith("Simulated:") for action in incident.response_actions)
        assert len(simulation.events) == 9


def test_failed_simulation_rolls_back_and_stores_event(app, monkeypatch):
    original = simulation_engine.populate_run

    def fail_after_population(simulation, actor):
        original(simulation, actor)
        db.session.flush()
        raise RuntimeError("Simulated test failure")

    monkeypatch.setattr(simulation_engine, "populate_run", fail_after_population)
    with app.app_context():
        run = simulation_engine.run_simulation("Phishing Attack", uuid4().hex, "admin")
        simulation = db.session.get(Simulation, run)
        assert simulation.status == "Failed"
        assert simulation.incident is None
        assert [event.status for event in simulation.events] == ["Failed"]
        assert db.session.scalar(select(func.count()).select_from(Incident)) == 0


def test_simulation_report_preserves_run_risk_after_later_reassessment(app, signed_in):
    with app.app_context():
        run_id = simulation_engine.run_simulation("Phishing Attack", uuid4().hex, "admin")
        incident = db.session.get(Simulation, run_id).incident
        incident.assessments.append(build_assessment("Residual", 1, 1))
        db.session.commit()
    report = signed_in.get(f"/simulations/{run_id}").data
    assert b"6 / 25" in report
    assert b"1 / 25" not in report


def test_interrupted_simulation_is_recovered(app):
    with app.app_context():
        old = Simulation(scenario_type="Phishing Attack", status="Running",
                         started_at=utc_now() - timedelta(minutes=10))
        fresh = Simulation(scenario_type="Malware Infection", status="Running", started_at=utc_now())
        db.session.add_all([old, fresh])
        db.session.commit()
        assert simulation_engine.recover_interrupted_runs() == 1
        assert old.status == "Failed"
        assert old.events[0].status == "Failed"
        assert fresh.status == "Running"
        assert simulation_engine.recover_interrupted_runs() == 0


def test_concurrent_requests_claim_one_run(tmp_path):
    class FileTestingConfig(TestingConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{(tmp_path / 'parallel.db').as_posix()}"

    app = create_app(FileTestingConfig)
    with app.app_context():
        db.create_all()

    key = uuid4().hex

    def start():
        with app.app_context():
            return simulation_engine.run_simulation("Phishing Attack", key, "admin")

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [pool.submit(start) for _ in range(2)]
        assert len({result.result(timeout=10) for result in results}) == 1
    with app.app_context():
        assert db.session.scalars(select(Simulation)).one().status == "Completed"
        assert db.session.scalar(select(func.count()).select_from(Incident)) == 1
        db.engine.dispose()

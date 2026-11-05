import sqlite3

from conftest import csrf_token
from extensions import db
from models import Incident, User
from modules.risk_engine import build_assessment
from test_database import migrated_app
from test_incidents import create_incident


def sign_in(app, username, role):
    with app.app_context():
        user = User(username=username, role=role)
        user.set_password("workspace-password")
        db.session.add(user)
        db.session.commit()
    client = app.test_client()
    assert client.post("/login", data={
        "csrf_token": csrf_token(client.get("/login")), "username": username,
        "password": "workspace-password",
    }).status_code == 302
    return client


def submit(client, path, **data):
    return client.post(path, data={"csrf_token": csrf_token(client.get(path)), **data})


def test_reviewers_cannot_modify_cases(app):
    reviewer = sign_in(app, "reader", "reviewer")
    assert reviewer.get("/incidents/").status_code == 200
    assert reviewer.get("/incidents/new").status_code == 403
    token = csrf_token(reviewer.get("/"))
    for path in ("/simulations/", "/alerts/import", "/assets/new", "/incidents/new"):
        assert reviewer.post(path, data={"csrf_token": token}).status_code == 403
    assert reviewer.get("/governance/audit").status_code == 200


def test_acceptance_requires_supervisor_and_records_audit(app, signed_in):
    analyst = sign_in(app, "operator", "analyst")
    incident_id = int(create_incident(analyst).rsplit("/", 1)[1])
    with app.app_context():
        incident = db.session.get(Incident, incident_id)
        incident.assessments.append(build_assessment("Initial", 4, 5))
        db.session.commit()
    register = f"/risks/{incident_id}"
    fields = {"owner": "Security", "review_date": "2026-12-01", "status": "Accepted"}
    assert b"request for approval" in submit(analyst, register, **fields).data
    assert submit(analyst, register, **{**fields, "status": "Open"}).status_code == 302
    assert submit(analyst, f"/governance/request/{incident_id}", reason="Short maintenance window").status_code == 302
    assert analyst.get("/governance/1/approve").status_code == 403
    assert submit(signed_in, "/governance/1/approve", reason="Reviewed mitigation").status_code == 302
    assert b"Reviewed mitigation" in signed_in.get("/governance/audit").data
    with app.app_context():
        assert db.session.get(Incident, incident_id).register_entry.status == "Accepted"


def test_backup_restores_schema_and_rejects_overwrite(migrated_app, tmp_path):
    with migrated_app.app_context():
        user = User(username="backup-owner")
        user.set_password("temporary-password")
        db.session.add(user)
        db.session.commit()
    path = tmp_path / "restored.db"
    runner = migrated_app.test_cli_runner()
    result = runner.invoke(args=["backup-db", str(path)])
    assert result.exit_code == 0, result.output
    assert runner.invoke(args=["backup-db", str(path)]).exit_code != 0
    connection = sqlite3.connect(path)
    try:
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert connection.execute("SELECT count(*) FROM audit_events").fetchone() == (0,)
        assert connection.execute("SELECT username FROM users").fetchone() == ("backup-owner",)
    finally:
        connection.close()

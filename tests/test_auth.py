from conftest import csrf_token
from extensions import db
from models import Incident, RiskAssessment, Simulation
from models.timestamps import utc_now


def test_private_dashboard_redirects(client):
    assert client.get("/").location.startswith("/login")


def test_invalid_password_rejected(client):
    token = csrf_token(client.get("/login"))
    response = client.post("/login", data={
        "csrf_token": token, "username": "admin", "password": "wrong",
    })
    assert b"Invalid username or password." in response.data
    assert client.get("/").status_code == 302


def test_dashboard_database_metrics_and_logout(app, signed_in):
    with app.app_context():
        incident = Incident(title="Mailbox alert", description="Reported by helpdesk.",
                            incident_type="Phishing Attack", severity="High", detected_at=utc_now(),
                            reported_by="Helpdesk", affected_asset="Mailbox")
        incident.assessments.extend([
            RiskAssessment(kind="Initial", likelihood=4, impact=5, score=20, level="Critical"),
            RiskAssessment(kind="Residual", likelihood=2, impact=3, score=6, level="Medium"),
        ])
        db.session.add_all([incident, Simulation(scenario_type="Phishing Attack")])
        db.session.commit()
    dashboard = signed_in.get("/")
    assert b"Mailbox alert" in dashboard.data
    assert b'"Medium": 1' in dashboard.data
    assert b'"Critical": 0' in dashboard.data
    assert b'"Open": 1' in dashboard.data
    assert signed_in.post("/logout", data={"csrf_token": csrf_token(dashboard)}).location == "/login"
    assert signed_in.get("/").status_code == 302

import pytest

from conftest import csrf_token
from extensions import db
from models import Incident
from modules.risk_engine import calculate_risk, classify_score
from test_incidents import create_incident


@pytest.mark.parametrize(("score", "level"), [
    (1, "Low"), (4, "Low"), (5, "Medium"), (9, "Medium"),
    (10, "High"), (16, "High"), (17, "Critical"), (25, "Critical"),
])
def test_classification_boundaries(score, level):
    assert classify_score(score) == level


@pytest.mark.parametrize("value", [False, 0, 6, 3.0, 2.5, "2", None])
def test_calculation_validates_both_inputs(value):
    with pytest.raises(ValueError):
        calculate_risk(value, 3)
    with pytest.raises(ValueError):
        calculate_risk(3, value)


def test_risk_flow_preserves_initial_and_history(app, signed_in):
    path = create_incident(signed_in)
    initial = path + "/risk/initial"
    residual = path + "/risk/residual"
    assert signed_in.get(residual).status_code == 409
    token = csrf_token(signed_in.get(initial))
    assert signed_in.post(initial, data={
        "csrf_token": token, "likelihood": 4, "impact": 5,
    }).status_code == 302
    assert signed_in.get(initial).status_code == 409
    token = csrf_token(signed_in.get(residual))
    mitigation = {
        "csrf_token": token, "impact": 3, "mitigation_actions": "Revoked sessions",
        "control_description": "Session invalidation", "mitigation_at": "2026-01-02T10:00",
        "responsible_person": "Analyst", "notes": "Verified the change",
    }
    assert signed_in.post(residual, data={**mitigation, "likelihood": 2}).status_code == 302
    response = signed_in.get(path)
    assert b"20 / 25" in response.data and b"6 / 25" in response.data
    assert b"Critical" in response.data and b"Medium" in response.data
    assert signed_in.post(residual, data={**mitigation, "likelihood": 1}).status_code == 302
    with app.app_context():
        incident = db.session.get(Incident, int(path.rsplit("/", 1)[1]))
        assert [(risk.score, risk.level) for risk in incident.assessments] == [
            (20, "Critical"), (6, "Medium"), (3, "Low"),
        ]
        assert incident.latest_residual_risk.mitigation_actions == "Revoked sessions"

from conftest import csrf_token
from extensions import db
from models import Incident
from test_incidents import create_incident


def test_response_actions_are_validated_and_persisted(app, signed_in):
    incident = create_incident(signed_in)
    path = incident + "/response/new"
    token = csrf_token(signed_in.get(path))
    data = {
        "csrf_token": token, "description": "Reviewed the endpoint alert",
        "responsible_person": "Analyst", "action_at": "2026-01-02T09:00", "notes": "Case documented.",
    }
    assert b"Not a valid choice" in signed_in.post(path, data={**data, "stage": "Unknown"}).data
    assert signed_in.post(path, data={**data, "stage": "Detection and Analysis"}).status_code == 302
    assert b"1 of 6 stages recorded" in signed_in.get(incident).data
    assert b"Reviewed the endpoint alert" in signed_in.get("/response/").data
    with app.app_context():
        stored = db.session.get(Incident, int(incident.rsplit("/", 1)[1]))
        action, = stored.response_actions
        assert action.incident is stored
        assert action.notes == "Case documented."
        assert action.action_at.hour == 9

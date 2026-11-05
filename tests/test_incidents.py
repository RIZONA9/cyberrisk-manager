from conftest import csrf_token
from extensions import db
from models import Incident


def incident_payload():
    return {
        "title": "Phishing report", "description": "Suspicious link from a sender.",
        "incident_type": "Phishing Attack", "severity": "High", "status": "Open",
        "detected_at": "2026-01-02T08:30", "reported_by": "Helpdesk", "affected_asset": "Mailbox",
    }


def create_incident(client):
    page = client.get("/incidents/new")
    response = client.post("/incidents/new", data={
        **incident_payload(), "csrf_token": csrf_token(page),
    })
    assert response.status_code == 302
    return response.location


def test_incident_crud_search_and_history(app, signed_in):
    path = create_incident(signed_in)
    assert b"Phishing report" in signed_in.get(path).data
    assert b"Phishing report" in signed_in.get("/incidents/?q=sender&severity=High&status=Open").data
    assert b"No matching incidents" in signed_in.get("/incidents/?severity=Low").data
    token = csrf_token(signed_in.get(path + "/edit"))
    assert signed_in.post(path + "/edit", data={
        **incident_payload(), "title": "Updated report", "status": "Closed", "csrf_token": token,
    }).status_code == 302
    assert b"Updated report" in signed_in.get(path).data
    confirm = signed_in.get(path + "/delete")
    assert b"Confirm deletion" in confirm.data
    assert signed_in.post(path + "/delete", data={"csrf_token": csrf_token(confirm)}).status_code == 302
    assert b"Archived" in signed_in.get(path).data
    assert signed_in.get(path + "/edit").status_code == 404
    assert b"Updated report" not in signed_in.get("/incidents/").data
    assert b"Updated report" in signed_in.get("/incidents/?scope=archive").data
    with app.app_context():
        incident = db.session.get(Incident, int(path.rsplit("/", 1)[1]))
        assert incident.archived_at is not None
        assert {entry.event for entry in incident.history} == {"Created", "Edited", "Archived"}


def test_incident_validation_and_authentication(client, signed_in):
    anonymous = client.application.test_client()
    assert anonymous.get("/incidents/").location.startswith("/login")
    token = csrf_token(signed_in.get("/incidents/new"))
    response = signed_in.post("/incidents/new", data={
        **incident_payload(), "title": "  ", "severity": "Unknown", "csrf_token": token,
    })
    assert response.status_code == 200
    assert b"Not a valid choice" in response.data
    assert b"No matching incidents" in signed_in.get("/incidents/").data

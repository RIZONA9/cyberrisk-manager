from conftest import csrf_token
from extensions import db
from models import Incident
from test_incidents import incident_payload


def test_register_asset_and_link_incident(app, signed_in):
    form = signed_in.get("/assets/new")
    data = {
        "csrf_token": csrf_token(form), "identifier": "LAB-DC-01", "name": "Identity server",
        "category": "Server", "owner": "IT operations", "criticality": "Critical",
        "environment": "Lab", "internet_exposed": "y",
    }
    asset = signed_in.post("/assets/new", data=data)
    assert asset.status_code == 302
    assert b"already exists" in signed_in.post("/assets/new", data=data).data
    form = signed_in.get("/incidents/new")
    incident = signed_in.post("/incidents/new", data={
        **incident_payload(), "affected_asset": "", "asset_id": asset.location.rsplit("/", 1)[1],
        "csrf_token": csrf_token(form),
    })
    assert incident.status_code == 302
    assert b"Identity server" in signed_in.get(incident.location).data
    assert b"Phishing report" in signed_in.get(asset.location).data
    with app.app_context():
        stored = db.session.get(Incident, int(incident.location.rsplit("/", 1)[1]))
        assert stored.asset.identifier == "lab-dc-01"
        assert stored.asset.internet_exposed
        assert stored.affected_asset == "Identity server"

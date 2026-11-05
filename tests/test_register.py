from conftest import csrf_token
from extensions import db
from models import Incident
from modules.risk_engine import build_assessment
from test_incidents import create_incident


def test_risk_register_filters_sorting_and_metadata(app, signed_in):
    low = create_incident(signed_in)
    high = create_incident(signed_in)
    low_id, high_id = [int(path.rsplit("/", 1)[1]) for path in (low, high)]
    with app.app_context():
        for incident_id, title, impact in [(low_id, "Alpha case", 1), (high_id, "Zulu case", 5)]:
            incident = db.session.get(Incident, incident_id)
            incident.title = title
            incident.assessments.append(build_assessment("Initial", impact, impact))
        db.session.commit()

    path = f"/risks/{high_id}"
    token = csrf_token(signed_in.get(path))
    assert signed_in.post(path, data={
        "csrf_token": token, "owner": "Security team", "review_date": "2026-12-01",
        "status": "Monitoring",
    }).status_code == 302
    filtered = signed_in.get("/risks/?q=Security+team&level=Critical&status=Monitoring").data
    assert b"Zulu case" in filtered and b"Alpha case" not in filtered
    assert b"No matching risks" in signed_in.get("/risks/?status=Accepted").data
    by_score = signed_in.get("/risks/").data
    by_title = signed_in.get("/risks/?sort=title").data
    assert by_score.index(b"Zulu case") < by_score.index(b"Alpha case")
    assert by_title.index(b"Alpha case") < by_title.index(b"Zulu case")
    with app.app_context():
        incident = db.session.get(Incident, high_id)
        assert incident.register_entry.owner == "Security team"
        assert str(incident.register_entry.review_date) == "2026-12-01"

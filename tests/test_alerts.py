import io
from pathlib import Path

from sqlalchemy import select

from conftest import csrf_token
from extensions import db
from models import Alert, Asset


def test_upload_deduplicates_and_converts_once(app, signed_in):
    with app.app_context():
        db.session.add(Asset(identifier="lab-ssh-01", name="Lab server", category="Server",
                             owner="Lab", criticality="High", environment="Lab"))
        db.session.commit()
    path = "/alerts/import"
    csrf = csrf_token(signed_in.get(path))
    raw = (Path(__file__).resolve().parents[1] / "examples" / "wazuh-alerts.jsonl").read_bytes()
    for expected in (b"Imported 2 alerts", b"Imported 0 alerts"):
        response = signed_in.post(path, data={
            "csrf_token": csrf, "source": "Wazuh-Lab", "upload": (io.BytesIO(raw), "alerts.jsonl"),
        }, follow_redirects=True)
        assert expected in response.data
    detail = "/alerts/1"
    csrf = csrf_token(signed_in.get(detail))
    first = signed_in.post(detail + "/convert", data={"csrf_token": csrf})
    assert first.status_code == 302
    assert signed_in.post(detail + "/convert", data={"csrf_token": csrf}).location == first.location
    with app.app_context():
        alert = db.session.scalar(select(Alert).where(Alert.external_id == "training-001"))
        assert alert.incident.asset.name == "Lab server"
        assert alert.incident.severity == "High"
        assert alert.incident.detected_at == alert.occurred_at

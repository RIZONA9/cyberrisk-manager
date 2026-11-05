from io import BytesIO
from pathlib import Path

from conftest import csrf_token
from extensions import db
from models import Asset


def test_import_findings_priority_and_remediation(app, signed_in):
    with app.app_context():
        db.session.add(Asset(identifier="lab-ssh-01", name="Lab SSH", category="Server",
                             owner="Lab", criticality="High", environment="Lab"))
        db.session.commit()
    raw = (Path(__file__).resolve().parents[1] / "examples" / "vulnerability-findings.csv").read_bytes()
    assert signed_in.get("/vulnerabilities/example").data == raw
    path = "/vulnerabilities/import"
    token = csrf_token(signed_in.get(path))
    for expected in (b"Saved 1 findings", b"Saved 0 findings"):
        response = signed_in.post(path, data={
            "csrf_token": token, "upload": (BytesIO(raw), "findings.csv"),
        }, follow_redirects=True)
        assert expected in response.data
        assert b"Known exploitation in CISA KEV" in response.data
        assert b"64.0%" in response.data
    resolve = "/vulnerabilities/1/resolve"
    assert signed_in.post(resolve, data={
        "csrf_token": csrf_token(signed_in.get(resolve)), "reason": "Verified a patched version",
    }).status_code == 302
    assert b"No findings" in signed_in.get("/vulnerabilities/").data
    assert b"CVE-2025-999999" in signed_in.get("/vulnerabilities/?scope=Resolved").data

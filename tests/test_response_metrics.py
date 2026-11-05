from datetime import datetime, timedelta

from extensions import db
from models import Alert, Incident, ResponseAction, Simulation
from modules.response_metrics import response_metrics


def test_medians_overdue_and_provenance(app, signed_in):
    detected = datetime(2026, 1, 1, 8)
    with app.app_context():
        def incident(severity="High"):
            return Incident(title="Case", description="Test", incident_type="Other", severity=severity,
                            detected_at=detected, reported_by="Test", affected_asset="Host")

        first, second, imported, synthetic = incident(), incident("Critical"), incident(), incident()
        first.first_observed_at = detected - timedelta(hours=2)
        first.response_actions.append(ResponseAction(
            stage="Containment", description="Contained", responsible_person="Operator",
            action_at=detected + timedelta(hours=3),
        ))
        db.session.add_all([first, second, Alert(
            source="wazuh", external_id="test", rule_id="12", level=5, description="Alert",
            agent_name="Host", occurred_at=detected, incident=imported,
        ), Simulation(scenario_type="Phishing Attack", incident=synthetic)])
        db.session.commit()
        stats = response_metrics(detected + timedelta(hours=12))
        assert stats["Manual"]["durations"] == [
            ("Detection", 2, 1), ("Containment", 3, 1), ("Recovery", None, 0),
        ]
        assert stats["Manual"]["overdue"] == 1
        assert stats["Imported"]["total"] == stats["Simulation"]["total"] == 1
        assert stats["Demo"]["total"] == 0
    assert b"Response metrics" in signed_in.get("/metrics/response").data

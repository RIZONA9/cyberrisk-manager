from sqlalchemy import case, select
from sqlalchemy.orm import aliased

from models import Incident, RiskAssessment


def current_risk_id():
    """Select the newest residual assessment, falling back to initial risk."""
    assessment = aliased(RiskAssessment)
    return (
        select(assessment.id).where(assessment.incident_id == Incident.id)
        .order_by(case((assessment.kind == "Residual", 0), else_=1),
                  assessment.assessed_at.desc(), assessment.id.desc())
        .limit(1).correlate(Incident).scalar_subquery()
    )

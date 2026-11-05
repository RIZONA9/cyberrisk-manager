from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from extensions import db
from models.timestamps import utc_now

if TYPE_CHECKING:
    from models.incident import Incident


class RiskAssessment(db.Model):
    __tablename__ = "risk_assessments"
    __table_args__ = (
        CheckConstraint("kind IN ('Initial', 'Residual')", name="kind"),
        CheckConstraint(
            "typeof(likelihood) = 'integer' AND likelihood BETWEEN 1 AND 5",
            name="likelihood_range",
        ),
        CheckConstraint(
            "typeof(impact) = 'integer' AND impact BETWEEN 1 AND 5",
            name="impact_range",
        ),
        CheckConstraint(
            "typeof(score) = 'integer' AND score BETWEEN 1 AND 25", name="score_range"
        ),
        CheckConstraint("level IN ('Low', 'Medium', 'High', 'Critical')", name="level"),
        Index(
            "uq_risk_assessments_initial_incident",
            "incident_id",
            unique=True,
            sqlite_where=text("kind = 'Initial'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(
        ForeignKey("incidents.id", ondelete="RESTRICT"), index=True
    )
    kind: Mapped[str] = mapped_column(String(8))
    likelihood: Mapped[int]
    impact: Mapped[int]
    score: Mapped[int]
    level: Mapped[str] = mapped_column(String(8))
    assessed_at: Mapped[datetime] = mapped_column(default=utc_now)
    mitigation_actions: Mapped[str | None] = mapped_column(Text)
    control_description: Mapped[str | None] = mapped_column(Text)
    mitigation_at: Mapped[datetime | None]
    responsible_person: Mapped[str | None] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(Text)

    incident: Mapped[Incident] = relationship(back_populates="assessments")

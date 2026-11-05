from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from extensions import db
from models.incident import Incident
from models.timestamps import utc_now


class AuditEvent(db.Model):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor: Mapped[str] = mapped_column(String(80))
    action: Mapped[str] = mapped_column(String(60))
    target: Mapped[str] = mapped_column(String(140))
    before: Mapped[str | None] = mapped_column(Text)
    after: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(default=utc_now)


class RiskAcceptance(db.Model):
    __tablename__ = "risk_acceptances"
    __table_args__ = (
        CheckConstraint("status IN ('Pending', 'Approved', 'Rejected')", name="status"),
        Index("uq_risk_acceptances_pending", "incident_id", unique=True,
              sqlite_where=text("status = 'Pending'")),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id", ondelete="RESTRICT"))
    assessment_id: Mapped[int] = mapped_column(ForeignKey("risk_assessments.id", ondelete="RESTRICT"))
    requested_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    requested_at: Mapped[datetime] = mapped_column(default=utc_now)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(8), default="Pending")
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    reviewed_at: Mapped[datetime | None]
    decision_reason: Mapped[str | None] = mapped_column(Text)
    incident: Mapped[Incident] = relationship()

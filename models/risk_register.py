from datetime import date

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from extensions import db


RISK_STATUSES = ("Open", "Monitoring", "Accepted", "Closed")


class RiskRegisterEntry(db.Model):
    __tablename__ = "risk_register_entries"
    __table_args__ = (
        CheckConstraint("status IN ('Open', 'Monitoring', 'Accepted', 'Closed')", name="status"),
    )

    incident_id: Mapped[int] = mapped_column(
        ForeignKey("incidents.id", ondelete="RESTRICT"), primary_key=True,
    )
    owner: Mapped[str] = mapped_column(String(120))
    review_date: Mapped[date]
    status: Mapped[str] = mapped_column(String(12))

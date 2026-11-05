from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from extensions import db
from models.timestamps import utc_now

if TYPE_CHECKING:
    from models.incident import Incident


RESPONSE_STAGES = (
    "Preparation", "Detection and Analysis", "Containment",
    "Eradication", "Recovery", "Lessons Learned",
)


class ResponseAction(db.Model):
    __tablename__ = "response_actions"
    __table_args__ = (
        CheckConstraint(
            "stage IN ('Preparation', 'Detection and Analysis', 'Containment', "
            "'Eradication', 'Recovery', 'Lessons Learned')",
            name="stage",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(
        ForeignKey("incidents.id", ondelete="RESTRICT"), index=True
    )
    stage: Mapped[str] = mapped_column(String(30))
    description: Mapped[str] = mapped_column(Text)
    responsible_person: Mapped[str] = mapped_column(String(120))
    action_at: Mapped[datetime] = mapped_column(default=utc_now)
    notes: Mapped[str | None] = mapped_column(Text)

    incident: Mapped[Incident] = relationship(back_populates="response_actions")

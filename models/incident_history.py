from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from extensions import db
from models.timestamps import utc_now

if TYPE_CHECKING:
    from models.incident import Incident


class IncidentHistory(db.Model):
    __tablename__ = "incident_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(
        ForeignKey("incidents.id", ondelete="RESTRICT"), index=True
    )
    event: Mapped[str] = mapped_column(String(40))
    actor: Mapped[str] = mapped_column(String(80))
    details: Mapped[str] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(default=utc_now)
    incident: Mapped[Incident] = relationship(back_populates="history")

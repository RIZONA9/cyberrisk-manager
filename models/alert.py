from datetime import datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from extensions import db
from models.asset import Asset
from models.incident import Incident
from models.timestamps import utc_now


class Alert(db.Model):
    __tablename__ = "alerts"
    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_alerts_source_event"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(80))
    external_id: Mapped[str] = mapped_column(String(120))
    rule_id: Mapped[str] = mapped_column(String(80))
    level: Mapped[int]
    description: Mapped[str] = mapped_column(String(1000))
    agent_name: Mapped[str] = mapped_column(String(120))
    occurred_at: Mapped[datetime]
    imported_at: Mapped[datetime] = mapped_column(default=utc_now)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id", ondelete="RESTRICT"), index=True)
    incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id", ondelete="RESTRICT"), unique=True)
    asset: Mapped[Asset | None] = relationship()
    incident: Mapped[Incident | None] = relationship()

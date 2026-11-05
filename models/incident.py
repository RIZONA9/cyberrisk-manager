from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from extensions import db
from models.asset import Asset
from models.incident_history import IncidentHistory
from models.response import ResponseAction
from models.risk import RiskAssessment
from models.risk_register import RiskRegisterEntry
from models.timestamps import utc_now

if TYPE_CHECKING:
    from models.simulation import Simulation


class Incident(db.Model):
    __tablename__ = "incidents"
    __table_args__ = (
        CheckConstraint("severity IN ('Low', 'Medium', 'High', 'Critical')", name="severity"),
        CheckConstraint("status IN ('Open', 'In Progress', 'Closed')", name="status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    incident_type: Mapped[str] = mapped_column(String(80))
    severity: Mapped[str] = mapped_column(String(8))
    status: Mapped[str] = mapped_column(String(20), default="Open")
    detected_at: Mapped[datetime]
    first_observed_at: Mapped[datetime | None]
    reported_by: Mapped[str] = mapped_column(String(120))
    affected_asset: Mapped[str] = mapped_column(String(200))
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id"), index=True)
    asset: Mapped[Asset | None] = relationship()
    assigned_to: Mapped[str | None] = mapped_column(String(120))
    resolution_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(default=utc_now, onupdate=utc_now)
    archived_at: Mapped[datetime | None]
    demo_key: Mapped[str | None] = mapped_column(String(80), index=True, unique=True)

    register_entry: Mapped[RiskRegisterEntry | None] = relationship(passive_deletes="all")

    history: Mapped[list[IncidentHistory]] = relationship(
        back_populates="incident",
        passive_deletes="all",
        order_by=lambda: (IncidentHistory.occurred_at.desc(), IncidentHistory.id.desc()),
    )

    assessments: Mapped[list[RiskAssessment]] = relationship(
        back_populates="incident",
        passive_deletes="all",
        order_by=lambda: (RiskAssessment.assessed_at, RiskAssessment.id),
    )
    response_actions: Mapped[list[ResponseAction]] = relationship(
        back_populates="incident", passive_deletes="all",
        order_by=lambda: (ResponseAction.action_at.desc(), ResponseAction.id.desc()),
    )
    simulations: Mapped[list[Simulation]] = relationship(
        back_populates="incident", passive_deletes="all"
    )

    @property
    def initial_risk(self) -> RiskAssessment | None:
        return next((risk for risk in self.assessments if risk.kind == "Initial"), None)

    @property
    def latest_residual_risk(self) -> RiskAssessment | None:
        return next((risk for risk in reversed(self.assessments) if risk.kind == "Residual"), None)

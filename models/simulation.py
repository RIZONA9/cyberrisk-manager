from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from extensions import db
from models.timestamps import utc_now

if TYPE_CHECKING:
    from models.incident import Incident


class Simulation(db.Model):
    __tablename__ = "simulations"
    __table_args__ = (
        Index("ix_simulations_request_key", "request_key", unique=True),
        CheckConstraint(
            "status IN ('Pending', 'Running', 'Completed', 'Failed')", name="status"
        ),
        CheckConstraint(
            "ended_at IS NULL OR (started_at IS NOT NULL AND ended_at >= started_at)",
            name="time_order",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    scenario_type: Mapped[str] = mapped_column(String(80))
    request_key: Mapped[str | None] = mapped_column(String(32))
    incident_id: Mapped[int | None] = mapped_column(
        ForeignKey("incidents.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[str] = mapped_column(String(12), default="Pending")
    started_at: Mapped[datetime | None]
    ended_at: Mapped[datetime | None]
    result_summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)

    incident: Mapped[Incident | None] = relationship(back_populates="simulations")
    events: Mapped[list[SimulationEvent]] = relationship(
        back_populates="simulation",
        passive_deletes="all",
        order_by=lambda: (SimulationEvent.occurred_at, SimulationEvent.id),
    )


class SimulationEvent(db.Model):
    __tablename__ = "simulation_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    simulation_id: Mapped[int] = mapped_column(
        ForeignKey("simulations.id", ondelete="RESTRICT"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(default=utc_now)
    status: Mapped[str] = mapped_column(String(30))

    simulation: Mapped[Simulation] = relationship(back_populates="events")

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from extensions import db
from models.timestamps import utc_now


class ExerciseRun(db.Model):
    __tablename__ = "exercise_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    scenario: Mapped[str] = mapped_column(String(80))
    step: Mapped[int] = mapped_column(default=0)
    started_at: Mapped[datetime] = mapped_column(default=utc_now)
    ended_at: Mapped[datetime | None]
    decisions: Mapped[list["ExerciseDecision"]] = relationship(
        order_by="ExerciseDecision.step", passive_deletes="all",
    )


class ExerciseDecision(db.Model):
    __tablename__ = "exercise_decisions"
    __table_args__ = (UniqueConstraint("run_id", "step", name="uq_exercise_decisions_run_step"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("exercise_runs.id", ondelete="RESTRICT"))
    step: Mapped[int]
    choice: Mapped[str] = mapped_column(String(200))
    feedback: Mapped[str] = mapped_column(Text)
    evidence: Mapped[str | None] = mapped_column(Text)
    points: Mapped[int]
    seconds: Mapped[int]
    decided_at: Mapped[datetime] = mapped_column(default=utc_now)

"""Persist interactive exercise decisions."""
from alembic import op
import sqlalchemy as sa

revision = "c801006"
down_revision = "c801005"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "exercise_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("scenario", sa.String(80), nullable=False),
        sa.Column("step", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime()),
    )
    op.create_index("ix_exercise_runs_user_id", "exercise_runs", ["user_id"])
    op.create_table(
        "exercise_decisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("exercise_runs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("step", sa.Integer(), nullable=False),
        sa.Column("choice", sa.String(200), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=False),
        sa.Column("evidence", sa.Text()),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("seconds", sa.Integer(), nullable=False),
        sa.Column("decided_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("run_id", "step", name="uq_exercise_decisions_run_step"),
    )


def downgrade():
    op.drop_table("exercise_decisions")
    op.drop_table("exercise_runs")

"""Add roles, risk acceptance requests, and audit events."""
from alembic import op
import sqlalchemy as sa

revision = "c801004"
down_revision = "c801003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("role", sa.String(8), nullable=False, server_default="analyst"))
    op.execute("UPDATE users SET role = 'admin' WHERE username = 'admin'")
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor", sa.String(80), nullable=False),
        sa.Column("action", sa.String(60), nullable=False),
        sa.Column("target", sa.String(140), nullable=False),
        sa.Column("before", sa.Text()),
        sa.Column("after", sa.Text()),
        sa.Column("reason", sa.Text()),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "risk_acceptances",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("incident_id", sa.Integer(), sa.ForeignKey("incidents.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("assessment_id", sa.Integer(), sa.ForeignKey("risk_assessments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("requested_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("requested_at", sa.DateTime(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(8), nullable=False),
        sa.Column("reviewed_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT")),
        sa.Column("reviewed_at", sa.DateTime()),
        sa.Column("decision_reason", sa.Text()),
        sa.CheckConstraint("status IN ('Pending', 'Approved', 'Rejected')", name=op.f("ck_risk_acceptances_status")),
    )
    op.create_index("uq_risk_acceptances_pending", "risk_acceptances", ["incident_id"], unique=True,
                    sqlite_where=sa.text("status = 'Pending'"))


def downgrade():
    op.drop_table("risk_acceptances")
    op.drop_table("audit_events")
    op.execute("ALTER TABLE users DROP COLUMN role")

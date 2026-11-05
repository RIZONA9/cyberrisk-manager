"""Store normalized Wazuh alerts."""
from alembic import op
import sqlalchemy as sa

revision = "c801002"
down_revision = "c801001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", sa.String(80), nullable=False),
        sa.Column("external_id", sa.String(120), nullable=False),
        sa.Column("rule_id", sa.String(80), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(1000), nullable=False),
        sa.Column("agent_name", sa.String(120), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("imported_at", sa.DateTime(), nullable=False),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id", ondelete="RESTRICT")),
        sa.Column("incident_id", sa.Integer(), sa.ForeignKey("incidents.id", ondelete="RESTRICT"), unique=True),
        sa.UniqueConstraint("source", "external_id", name="uq_alerts_source_event"),
    )
    op.create_index("ix_alerts_asset_id", "alerts", ["asset_id"])


def downgrade():
    op.drop_table("alerts")

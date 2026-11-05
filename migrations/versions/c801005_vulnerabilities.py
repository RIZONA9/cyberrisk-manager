"""Add asset vulnerability findings."""
from alembic import op
import sqlalchemy as sa

revision = "c801005"
down_revision = "c801004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "vulnerabilities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("cve", sa.String(30), nullable=False),
        sa.Column("cvss", sa.Float()),
        sa.Column("epss", sa.Float()),
        sa.Column("kev", sa.Boolean()),
        sa.Column("source", sa.String(200), nullable=False),
        sa.Column("observed_on", sa.Date(), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.UniqueConstraint("asset_id", "cve", name="uq_vulnerabilities_asset_cve"),
    )
    op.create_index("ix_vulnerabilities_asset_id", "vulnerabilities", ["asset_id"])


def downgrade():
    op.drop_table("vulnerabilities")

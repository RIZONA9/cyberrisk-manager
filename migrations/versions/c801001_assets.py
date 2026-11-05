"""Add asset inventory and incident links."""
from alembic import op
import sqlalchemy as sa

revision = "c801001"
down_revision = "fadb819c8899"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("identifier", sa.String(120), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("owner", sa.String(120), nullable=False),
        sa.Column("criticality", sa.String(8), nullable=False),
        sa.Column("environment", sa.String(12), nullable=False),
        sa.Column("internet_exposed", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("identifier", name="uq_assets_identifier"),
    )
    # Add the nullable reference in place to preserve existing incident history.
    op.execute("ALTER TABLE incidents ADD COLUMN asset_id INTEGER "
               "CONSTRAINT fk_incidents_asset_id_assets REFERENCES assets(id)")
    op.create_index("ix_incidents_asset_id", "incidents", ["asset_id"])


def downgrade():
    op.drop_index("ix_incidents_asset_id", table_name="incidents")
    op.execute("ALTER TABLE incidents DROP COLUMN asset_id")
    op.drop_table("assets")

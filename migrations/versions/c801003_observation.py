"""Record first observed incident activity."""
from alembic import op
import sqlalchemy as sa

revision = "c801003"
down_revision = "c801002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("incidents", sa.Column("first_observed_at", sa.DateTime()))


def downgrade():
    op.execute("ALTER TABLE incidents DROP COLUMN first_observed_at")

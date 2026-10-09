"""store the offered creator payment on collaboration requests"""

from alembic import op
import sqlalchemy as sa


revision = "0012_collaboration_budget"
down_revision = "0011_remove_brand_role"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "collaboration_requests",
        sa.Column("budget", sa.Numeric(12, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("collaboration_requests", "budget")

"""add influencer designation to social accounts"""
from alembic import op
import sqlalchemy as sa

revision = "0002_add_is_influencer"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("social_accounts", sa.Column("is_influencer", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("social_accounts", "is_influencer")
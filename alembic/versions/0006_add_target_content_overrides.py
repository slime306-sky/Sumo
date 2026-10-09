"""add per-target content overrides"""
from alembic import op
import sqlalchemy as sa

revision = "0006_add_target_content_overrides"
down_revision = "0005_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("content_targets", sa.Column("caption", sa.Text(), nullable=True))
    op.add_column("content_targets", sa.Column("media_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("content_targets", "media_url")
    op.drop_column("content_targets", "caption")

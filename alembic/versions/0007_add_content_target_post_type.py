"""add content target post type"""
from alembic import op
import sqlalchemy as sa

revision = "0007_post_type"
down_revision = "0006_target_overrides"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("content_targets", sa.Column("post_type", sa.String(16), nullable=False, server_default="video"))
    op.alter_column("content_targets", "post_type", server_default=None)


def downgrade() -> None:
    op.drop_column("content_targets", "post_type")

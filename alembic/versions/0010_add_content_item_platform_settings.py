"""add platform settings to content items"""

from alembic import op
import sqlalchemy as sa


revision = "0010_content_item_platform_settings"
down_revision = "0009_add_platform_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "content_items",
        sa.Column("platform_settings", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.alter_column("content_items", "platform_settings", server_default=None)


def downgrade() -> None:
    op.drop_column("content_items", "platform_settings")

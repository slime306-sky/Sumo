"""add per-target platform settings"""

from alembic import op
import sqlalchemy as sa


revision = "0009_add_platform_settings"
down_revision = "0008_registration_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "content_targets",
        sa.Column("platform_settings", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.alter_column("content_targets", "platform_settings", server_default=None)


def downgrade() -> None:
    op.drop_column("content_targets", "platform_settings")

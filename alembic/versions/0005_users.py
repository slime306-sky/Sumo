"""add creator and brand login accounts"""
from alembic import op
import sqlalchemy as sa

revision = "0005_users"
down_revision = "0004_remove_instagram_linkedin"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("login_id", sa.String(120), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("role IN ('creator', 'brand')", name="ck_users_role"),
    )
    op.create_index("ix_users_login_id", "users", ["login_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_login_id", table_name="users")
    op.drop_table("users")

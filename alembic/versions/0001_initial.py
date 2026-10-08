"""create social account and video tables"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    platform = sa.Enum("instagram", "facebook", "linkedin", "youtube", name="platform", native_enum=False)
    op.create_table("social_accounts", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), nullable=False), sa.Column("platform", platform, nullable=False), sa.Column("platform_user_id", sa.String(255), nullable=False), sa.Column("access_token", sa.Text(), nullable=False), sa.Column("refresh_token", sa.Text()), sa.Column("token_expires_at", sa.DateTime(timezone=True)), sa.Column("platform_username", sa.String(255)), sa.Column("profile_name", sa.String(255)), sa.Column("profile_image_url", sa.Text()), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("user_id", "platform", "platform_user_id", name="uq_social_account_identity"))
    op.create_index("ix_social_accounts_user_id", "social_accounts", ["user_id"])
    op.create_table("social_videos", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("social_account_id", sa.Integer(), sa.ForeignKey("social_accounts.id", ondelete="CASCADE"), nullable=False), sa.Column("platform", sa.String(32), nullable=False), sa.Column("platform_video_id", sa.String(255), nullable=False), sa.Column("title", sa.Text()), sa.Column("description", sa.Text()), sa.Column("url", sa.Text()), sa.Column("thumbnail_url", sa.Text()), sa.Column("published_at", sa.DateTime(timezone=True)), sa.Column("duration", sa.Integer()), sa.Column("view_count", sa.Integer()), sa.Column("like_count", sa.Integer()), sa.Column("comment_count", sa.Integer()), sa.Column("raw_data", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("social_account_id", "platform_video_id", name="uq_social_video_identity"))
    op.create_index("ix_social_videos_social_account_id", "social_videos", ["social_account_id"])


def downgrade() -> None:
    op.drop_index("ix_social_videos_social_account_id", table_name="social_videos")
    op.drop_table("social_videos")
    op.drop_index("ix_social_accounts_user_id", table_name="social_accounts")
    op.drop_table("social_accounts")

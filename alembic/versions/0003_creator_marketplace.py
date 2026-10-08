"""add creator, content, analytics, and marketplace tables"""
from alembic import op
import sqlalchemy as sa

revision = "0003_creator_marketplace"
down_revision = "0002_add_is_influencer"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("creator_profiles", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), nullable=False), sa.Column("display_name", sa.String(255), nullable=False), sa.Column("bio", sa.Text()), sa.Column("niche", sa.String(120)), sa.Column("location", sa.String(255)), sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("user_id", name="uq_creator_profiles_user_id"))
    op.create_index("ix_creator_profiles_user_id", "creator_profiles", ["user_id"])
    op.create_table("brand_profiles", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), nullable=False), sa.Column("company_name", sa.String(255), nullable=False), sa.Column("description", sa.Text()), sa.Column("website", sa.Text()), sa.Column("industry", sa.String(120)), sa.Column("logo_url", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("user_id", name="uq_brand_profiles_user_id"))
    op.create_index("ix_brand_profiles_user_id", "brand_profiles", ["user_id"])
    op.create_table("content_items", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("creator_user_id", sa.Integer(), nullable=False), sa.Column("caption", sa.Text()), sa.Column("media_url", sa.Text()), sa.Column("status", sa.String(32), nullable=False, server_default="draft"), sa.Column("scheduled_at", sa.DateTime(timezone=True)), sa.Column("published_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_content_items_creator_user_id", "content_items", ["creator_user_id"])
    op.create_index("ix_content_items_status", "content_items", ["status"])
    op.create_table("content_targets", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("content_item_id", sa.Integer(), sa.ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False), sa.Column("social_account_id", sa.Integer(), sa.ForeignKey("social_accounts.id", ondelete="CASCADE"), nullable=False), sa.Column("platform_post_id", sa.String(255)), sa.Column("published_url", sa.Text()), sa.Column("status", sa.String(32), nullable=False, server_default="pending"), sa.UniqueConstraint("content_item_id", "social_account_id", name="uq_content_target_account"))
    op.create_index("ix_content_targets_content_item_id", "content_targets", ["content_item_id"])
    op.create_index("ix_content_targets_social_account_id", "content_targets", ["social_account_id"])
    op.create_table("campaigns", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("brand_user_id", sa.Integer(), nullable=False), sa.Column("title", sa.String(255), nullable=False), sa.Column("description", sa.Text()), sa.Column("requirements", sa.Text()), sa.Column("budget", sa.Numeric(12, 2)), sa.Column("starts_at", sa.DateTime(timezone=True)), sa.Column("ends_at", sa.DateTime(timezone=True)), sa.Column("status", sa.String(32), nullable=False, server_default="open"), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_campaigns_brand_user_id", "campaigns", ["brand_user_id"])
    op.create_index("ix_campaigns_status", "campaigns", ["status"])
    op.create_table("collaboration_requests", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("brand_user_id", sa.Integer(), nullable=False), sa.Column("creator_user_id", sa.Integer(), nullable=False), sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id", ondelete="SET NULL")), sa.Column("message", sa.Text()), sa.Column("status", sa.String(32), nullable=False, server_default="pending"), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_collaboration_requests_brand_user_id", "collaboration_requests", ["brand_user_id"])
    op.create_index("ix_collaboration_requests_creator_user_id", "collaboration_requests", ["creator_user_id"])
    op.create_index("ix_collaboration_requests_campaign_id", "collaboration_requests", ["campaign_id"])
    op.create_index("ix_collaboration_requests_status", "collaboration_requests", ["status"])
    op.create_table("account_metric_snapshots", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("social_account_id", sa.Integer(), sa.ForeignKey("social_accounts.id", ondelete="CASCADE"), nullable=False), sa.Column("follower_count", sa.Integer()), sa.Column("view_count", sa.Integer()), sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_account_metric_snapshots_social_account_id", "account_metric_snapshots", ["social_account_id"])
    op.create_index("ix_account_metric_snapshots_recorded_at", "account_metric_snapshots", ["recorded_at"])


def downgrade() -> None:
    op.drop_index("ix_account_metric_snapshots_recorded_at", table_name="account_metric_snapshots")
    op.drop_index("ix_account_metric_snapshots_social_account_id", table_name="account_metric_snapshots")
    op.drop_table("account_metric_snapshots")
    op.drop_index("ix_collaboration_requests_status", table_name="collaboration_requests")
    op.drop_index("ix_collaboration_requests_campaign_id", table_name="collaboration_requests")
    op.drop_index("ix_collaboration_requests_creator_user_id", table_name="collaboration_requests")
    op.drop_index("ix_collaboration_requests_brand_user_id", table_name="collaboration_requests")
    op.drop_table("collaboration_requests")
    op.drop_index("ix_campaigns_status", table_name="campaigns")
    op.drop_index("ix_campaigns_brand_user_id", table_name="campaigns")
    op.drop_table("campaigns")
    op.drop_index("ix_content_targets_social_account_id", table_name="content_targets")
    op.drop_index("ix_content_targets_content_item_id", table_name="content_targets")
    op.drop_table("content_targets")
    op.drop_index("ix_content_items_status", table_name="content_items")
    op.drop_index("ix_content_items_creator_user_id", table_name="content_items")
    op.drop_table("content_items")
    op.drop_index("ix_brand_profiles_user_id", table_name="brand_profiles")
    op.drop_table("brand_profiles")
    op.drop_index("ix_creator_profiles_user_id", table_name="creator_profiles")
    op.drop_table("creator_profiles")

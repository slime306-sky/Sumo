"""remove discontinued Instagram and LinkedIn accounts"""
from alembic import op

revision = "0004_remove_instagram_linkedin"
down_revision = "0003_creator_marketplace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DELETE FROM content_targets WHERE social_account_id IN (SELECT id FROM social_accounts WHERE platform IN ('instagram', 'linkedin'))")
    op.execute("DELETE FROM account_metric_snapshots WHERE social_account_id IN (SELECT id FROM social_accounts WHERE platform IN ('instagram', 'linkedin'))")
    op.execute("DELETE FROM social_videos WHERE social_account_id IN (SELECT id FROM social_accounts WHERE platform IN ('instagram', 'linkedin'))")
    op.execute("DELETE FROM social_accounts WHERE platform IN ('instagram', 'linkedin')")


def downgrade() -> None:
    pass
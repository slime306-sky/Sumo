"""replace the legacy brand role with company"""

from alembic import op
import sqlalchemy as sa


revision = "0011_remove_brand_role"
down_revision = "0010_content_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO companies (
            user_id, company_name, company_website, company_description,
            company_logo, industry
        )
        SELECT bp.user_id, bp.company_name, bp.website, bp.description,
               bp.logo_url, bp.industry
        FROM brand_profiles bp
        WHERE NOT EXISTS (
            SELECT 1 FROM companies c WHERE c.user_id = bp.user_id
        )
        """
    )
    op.execute("UPDATE users SET role = 'company' WHERE role = 'brand'")

    op.drop_constraint("ck_users_role", "users", type_="check")
    op.create_check_constraint("ck_users_role", "users", "role IN ('creator', 'company')")

    op.alter_column("campaigns", "brand_user_id", new_column_name="company_user_id")
    op.alter_column(
        "collaboration_requests",
        "brand_user_id",
        new_column_name="company_user_id",
    )
    op.drop_index("ix_brand_profiles_user_id", table_name="brand_profiles")
    op.drop_table("brand_profiles")


def downgrade() -> None:
    op.create_table(
        "brand_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("website", sa.Text()),
        sa.Column("industry", sa.String(120)),
        sa.Column("logo_url", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", name="uq_brand_profiles_user_id"),
    )
    op.create_index("ix_brand_profiles_user_id", "brand_profiles", ["user_id"])
    op.alter_column("campaigns", "company_user_id", new_column_name="brand_user_id")
    op.alter_column(
        "collaboration_requests",
        "company_user_id",
        new_column_name="brand_user_id",
    )
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.create_check_constraint("ck_users_role", "users", "role IN ('creator', 'brand', 'company')")

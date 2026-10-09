"""add registration profile data"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008_registration_profiles"
down_revision = "0007_post_type"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("users", "login_id", type_=sa.String(255), existing_type=sa.String(120), existing_nullable=False)
    op.add_column("users", sa.Column("email", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("status", sa.String(20), nullable=False, server_default="active"))
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.execute("UPDATE users SET email = login_id WHERE email IS NULL")
    op.alter_column("users", "email", nullable=False)
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.create_check_constraint("ck_users_role", "users", "role IN ('creator', 'brand', 'company')")

    op.create_table(
        "creators",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column("city_state", sa.String(150)),
        sa.Column("country", sa.String(100)),
        sa.Column("creator_category", sa.String(100)),
        sa.Column("content_experience", sa.String(100)),
        sa.Column("content_interests", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("personal_goal", sa.Text()),
        sa.Column("profile_pic", sa.Text()),
        sa.Column("purposes", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", name="uq_creators_user_id"),
    )
    op.create_index("ix_creators_user_id", "creators", ["user_id"])

    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_name", sa.String(200), nullable=False),
        sa.Column("company_size", sa.String(50)),
        sa.Column("company_website", sa.Text()),
        sa.Column("company_description", sa.Text()),
        sa.Column("company_logo", sa.Text()),
        sa.Column("city_state", sa.String(150)),
        sa.Column("country", sa.String(100)),
        sa.Column("industry", sa.String(100)),
        sa.Column("marketing_goal", sa.Text()),
        sa.Column("creator_categories", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("platforms", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("purposes", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("additional_notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", name="uq_companies_user_id"),
    )
    op.create_index("ix_companies_user_id", "companies", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_companies_user_id", table_name="companies")
    op.drop_table("companies")
    op.drop_index("ix_creators_user_id", table_name="creators")
    op.drop_table("creators")
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.create_check_constraint("ck_users_role", "users", "role IN ('creator', 'brand')")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_column("users", "updated_at")
    op.drop_column("users", "email_verified_at")
    op.drop_column("users", "status")
    op.drop_column("users", "email")
    op.alter_column("users", "login_id", type_=sa.String(120), existing_type=sa.String(255), existing_nullable=False)

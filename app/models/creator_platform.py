from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CreatorProfile(Base):
    __tablename__ = "creator_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    bio: Mapped[str | None] = mapped_column(Text)
    niche: Mapped[str | None] = mapped_column(String(120))
    location: Mapped[str | None] = mapped_column(String(255))
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class BrandProfile(Base):
    __tablename__ = "brand_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    website: Mapped[str | None] = mapped_column(Text)
    industry: Mapped[str | None] = mapped_column(String(120))
    logo_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ContentItem(Base):
    __tablename__ = "content_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    creator_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    caption: Mapped[str | None] = mapped_column(Text)
    media_url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False, index=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ContentTarget(Base):
    __tablename__ = "content_targets"
    __table_args__ = (UniqueConstraint("content_item_id", "social_account_id", name="uq_content_target_account"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    content_item_id: Mapped[int] = mapped_column(ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False, index=True)
    social_account_id: Mapped[int] = mapped_column(ForeignKey("social_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    platform_post_id: Mapped[str | None] = mapped_column(String(255))
    published_url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    brand_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    requirements: Mapped[str | None] = mapped_column(Text)
    budget: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class CollaborationRequest(Base):
    __tablename__ = "collaboration_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    brand_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    creator_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    campaign_id: Mapped[int | None] = mapped_column(ForeignKey("campaigns.id", ondelete="SET NULL"), index=True)
    message: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class AccountMetricSnapshot(Base):
    __tablename__ = "account_metric_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    social_account_id: Mapped[int] = mapped_column(ForeignKey("social_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    follower_count: Mapped[int | None] = mapped_column(Integer)
    view_count: Mapped[int | None] = mapped_column(Integer)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
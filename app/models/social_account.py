from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Platform(StrEnum):
    FACEBOOK = "facebook"
    YOUTUBE = "youtube"


class SocialAccount(Base):
    __tablename__ = "social_accounts"
    __table_args__ = (UniqueConstraint("user_id", "platform", "platform_user_id", name="uq_social_account_identity"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    platform: Mapped[Platform] = mapped_column(Enum(Platform, native_enum=False), nullable=False)
    platform_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(Text)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    platform_username: Mapped[str | None] = mapped_column(String(255))
    profile_name: Mapped[str | None] = mapped_column(String(255))
    profile_image_url: Mapped[str | None] = mapped_column(Text)
    is_influencer: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

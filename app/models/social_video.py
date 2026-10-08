from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.social_account import Platform


class SocialVideo(Base):
    __tablename__ = "social_videos"
    __table_args__ = (UniqueConstraint("social_account_id", "platform_video_id", name="uq_social_video_identity"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    social_account_id: Mapped[int] = mapped_column(ForeignKey("social_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    platform: Mapped[Platform] = mapped_column(String(32), nullable=False)
    platform_video_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    thumbnail_url: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration: Mapped[int | None] = mapped_column(Integer)
    view_count: Mapped[int | None] = mapped_column(Integer)
    like_count: Mapped[int | None] = mapped_column(Integer)
    comment_count: Mapped[int | None] = mapped_column(Integer)
    raw_data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

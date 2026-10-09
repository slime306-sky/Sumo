from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Creator(Base):
    __tablename__ = "creators"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    city_state: Mapped[str | None] = mapped_column(String(150))
    country: Mapped[str | None] = mapped_column(String(100))
    creator_category: Mapped[str | None] = mapped_column(String(100))
    content_experience: Mapped[str | None] = mapped_column(String(100))
    content_interests: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    personal_goal: Mapped[str | None] = mapped_column(Text)
    profile_pic: Mapped[str | None] = mapped_column(Text)
    purposes: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    user: Mapped["User"] = relationship(back_populates="creator")


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    company_size: Mapped[str | None] = mapped_column(String(50))
    company_website: Mapped[str | None] = mapped_column(Text)
    company_description: Mapped[str | None] = mapped_column(Text)
    company_logo: Mapped[str | None] = mapped_column(Text)
    city_state: Mapped[str | None] = mapped_column(String(150))
    country: Mapped[str | None] = mapped_column(String(100))
    industry: Mapped[str | None] = mapped_column(String(100))
    marketing_goal: Mapped[str | None] = mapped_column(Text)
    creator_categories: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    platforms: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    purposes: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    additional_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    user: Mapped["User"] = relationship(back_populates="company")

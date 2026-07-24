from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CreatorProfile(Base):
    __tablename__ = "creator_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    city_state: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str] = mapped_column(String(255), nullable=False)
    creator_category: Mapped[str] = mapped_column(String(255), nullable=False)
    content_experience: Mapped[str] = mapped_column(String(100), nullable=False)
    content_interests: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    persona_goal: Mapped[str | None] = mapped_column(String(255), nullable=True)
    profile_pic: Mapped[str | None] = mapped_column(String(500), nullable=True)
    purposes: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="creator_profile")


class CompanyProfile(Base):
    __tablename__ = "company_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    business_email: Mapped[str] = mapped_column(String(255), nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    company_size: Mapped[str] = mapped_column(String(100), nullable=False)
    company_website: Mapped[str] = mapped_column(String(500), nullable=False)
    company_description: Mapped[str] = mapped_column(String(2000), nullable=False)
    company_logo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    city_state: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str] = mapped_column(String(255), nullable=False)
    industry: Mapped[str] = mapped_column(String(255), nullable=False)
    marketing_goal: Mapped[str] = mapped_column(String(255), nullable=False)
    creator_categories: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    platforms: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    purposes: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    additional_notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="company_profile")

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.social_account import Platform


class CreatorSocialAccountResponse(BaseModel):
    platform: Platform
    platform_username: str | None = None
    profile_name: str | None = None
    profile_image_url: str | None = None
    is_influencer: bool


class CreatorProfileCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=255)
    bio: str | None = None
    niche: str | None = Field(default=None, max_length=120)
    location: str | None = Field(default=None, max_length=255)
    is_public: bool = True


class CreatorProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    bio: str | None = None
    niche: str | None = Field(default=None, max_length=120)
    location: str | None = Field(default=None, max_length=255)
    is_public: bool | None = None


class CreatorProfileResponse(CreatorProfileCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime
    social_accounts: list[CreatorSocialAccountResponse] = Field(default_factory=list)


class BrandProfileCreate(BaseModel):
    company_name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    website: str | None = None
    industry: str | None = Field(default=None, max_length=120)
    logo_url: str | None = None


class BrandProfileUpdate(BaseModel):
    company_name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    website: str | None = None
    industry: str | None = Field(default=None, max_length=120)
    logo_url: str | None = None


class BrandProfileResponse(BrandProfileCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime


class ContentCreate(BaseModel):
    caption: str | None = None
    media_url: str | None = None
    social_account_ids: list[int] = Field(default_factory=list)
    scheduled_at: datetime | None = None

    @model_validator(mode="after")
    def require_content(self):
        if not (self.caption or self.media_url):
            raise ValueError("Provide a caption or media URL")
        if len(self.social_account_ids) != len(set(self.social_account_ids)):
            raise ValueError("Social account IDs must be unique")
        if self.scheduled_at is not None and not self.social_account_ids:
            raise ValueError("Scheduled content requires at least one social account")
        return self


class ContentUpdate(BaseModel):
    caption: str | None = None
    media_url: str | None = None
    social_account_ids: list[int] | None = None
    scheduled_at: datetime | None = None


class ContentTargetResponse(BaseModel):
    id: int
    social_account_id: int
    platform_post_id: str | None = None
    published_url: str | None = None
    status: str


class ContentResponse(BaseModel):
    id: int
    creator_user_id: int
    caption: str | None = None
    media_url: str | None = None
    status: str
    scheduled_at: datetime | None = None
    published_at: datetime | None = None
    created_at: datetime
    targets: list[ContentTargetResponse]


class CampaignCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    requirements: str | None = None
    budget: Decimal | None = Field(default=None, ge=0)
    starts_at: datetime | None = None
    ends_at: datetime | None = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.starts_at and self.ends_at and self.ends_at < self.starts_at:
            raise ValueError("Campaign end must be after its start")
        return self


class CampaignUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    requirements: str | None = None
    budget: Decimal | None = Field(default=None, ge=0)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    status: Literal["draft", "open", "active", "completed", "cancelled"] | None = None


class CampaignResponse(CampaignCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    brand_user_id: int
    status: str
    created_at: datetime


class CollaborationCreate(BaseModel):
    creator_user_id: int
    campaign_id: int | None = None
    message: str | None = None


class CollaborationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    brand_user_id: int
    creator_user_id: int
    campaign_id: int | None = None
    message: str | None = None
    status: str
    created_at: datetime


class CollaborationDecision(BaseModel):
    status: Literal["accepted", "declined"]


class CollaborationProgress(BaseModel):
    status: Literal["in_progress", "completed", "cancelled"]


class MetricSnapshotCreate(BaseModel):
    follower_count: int | None = Field(default=None, ge=0)
    view_count: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def require_metric(self):
        if self.follower_count is None and self.view_count is None:
            raise ValueError("Provide at least one metric")
        return self


class MetricSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    social_account_id: int
    follower_count: int | None = None
    view_count: int | None = None
    recorded_at: datetime
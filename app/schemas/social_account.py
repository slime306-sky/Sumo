from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.social_account import Platform
from app.schemas.video import VideoResponse


class SocialAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    platform: Platform
    platform_user_id: str
    platform_username: str | None = None
    profile_name: str | None = None
    profile_image_url: str | None = None
    token_expires_at: datetime | None = None
    is_influencer: bool = False
    is_active: bool


class InfluencerUpdate(BaseModel):
    is_influencer: bool


class SyncResponse(BaseModel):
    account_id: int
    platform: Platform
    count: int
    videos: list[VideoResponse]

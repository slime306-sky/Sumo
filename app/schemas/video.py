from datetime import datetime

from pydantic import BaseModel, ConfigDict


class VideoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    platform_video_id: str
    title: str | None = None
    description: str | None = None
    url: str | None = None
    thumbnail_url: str | None = None
    published_at: datetime | None = None
    duration: int | None = None
    view_count: int | None = None
    like_count: int | None = None
    comment_count: int | None = None


class VideoListResponse(BaseModel):
    platform: str
    videos: list[VideoResponse]
    count: int

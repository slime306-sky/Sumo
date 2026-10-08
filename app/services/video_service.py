import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.integrations.base import VideoPage
from app.integrations.registry import get_integration
from app.models.social_account import SocialAccount
from app.models.social_video import SocialVideo
from app.services.social_account_service import SocialAccountService
from app.services.platform_service import PlatformService

logger = logging.getLogger(__name__)


class VideoService:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    async def list_videos(self, account: SocialAccount) -> list[SocialVideo]:
        PlatformService(self.settings).require_enabled(account.platform)
        result = await self.db.execute(select(SocialVideo).where(SocialVideo.social_account_id == account.id).order_by(SocialVideo.published_at.desc()))
        return list(result.scalars().all())

    async def sync(self, account: SocialAccount) -> list[SocialVideo]:
        PlatformService(self.settings).require_enabled(account.platform)
        token = await SocialAccountService(self.db, self.settings).valid_token(account)
        integration = get_integration(account.platform, self.settings)
        cursor = None
        while True:
            page: VideoPage = await integration.get_videos(token, cursor)
            for video in page.items:
                result = await self.db.execute(select(SocialVideo).where(SocialVideo.social_account_id == account.id, SocialVideo.platform_video_id == video.platform_video_id))
                record = result.scalar_one_or_none()
                values = {"platform": account.platform.value, "title": video.title, "description": video.description, "url": video.url, "thumbnail_url": video.thumbnail_url, "published_at": video.published_at, "duration": video.duration, "view_count": video.view_count, "like_count": video.like_count, "comment_count": video.comment_count, "raw_data": video.raw_data or {}}
                if record is None:
                    self.db.add(SocialVideo(social_account_id=account.id, platform_video_id=video.platform_video_id, **values))
                else:
                    for key, value in values.items():
                        setattr(record, key, value)
            if not page.next_cursor:
                break
            cursor = page.next_cursor
        await self.db.commit()
        return await self.list_videos(account)

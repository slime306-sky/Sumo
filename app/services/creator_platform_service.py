from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.time import assume_india_timezone, now_utc
from app.integrations.base import PlatformAPIError, SocialIntegrationError
from app.integrations.registry import get_integration
from app.models.creator_platform import AccountMetricSnapshot, BrandProfile, Campaign, CollaborationRequest, ContentItem, ContentTarget, CreatorProfile
from app.models.social_account import SocialAccount
from app.models.social_video import SocialVideo
from app.schemas.creator_platform import BrandProfileCreate, BrandProfileUpdate, CampaignCreate, CampaignUpdate, CollaborationCreate, ContentCreate, ContentUpdate, CreatorProfileCreate, CreatorProfileUpdate, MetricSnapshotCreate
from app.services.platform_service import PlatformService


class CreatorPlatformService:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    async def creator_profile(self, user_id: int) -> CreatorProfile | None:
        result = await self.db.execute(select(CreatorProfile).where(CreatorProfile.user_id == user_id))
        return result.scalar_one_or_none()

    async def save_creator_profile(self, user_id: int, values: CreatorProfileCreate | CreatorProfileUpdate) -> CreatorProfile:
        profile = await self.creator_profile(user_id)
        data = values.model_dump(exclude_unset=True)
        if profile is None:
            profile = CreatorProfile(user_id=user_id, **data)
            self.db.add(profile)
        else:
            for key, value in data.items():
                setattr(profile, key, value)
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def creator_profile_data(self, profile: CreatorProfile) -> dict:
        result = await self.db.execute(
            select(SocialAccount)
            .where(SocialAccount.user_id == profile.user_id, SocialAccount.is_active.is_(True))
            .order_by(SocialAccount.created_at.desc())
        )
        platform_service = PlatformService(self.settings)
        accounts = [account for account in result.scalars().all() if platform_service.is_enabled(account.platform)]
        return {
            "id": profile.id,
            "user_id": profile.user_id,
            "display_name": profile.display_name,
            "bio": profile.bio,
            "niche": profile.niche,
            "location": profile.location,
            "is_public": profile.is_public,
            "created_at": profile.created_at,
            "social_accounts": [
                {
                    "platform": account.platform,
                    "platform_username": account.platform_username,
                    "profile_name": account.profile_name,
                    "profile_image_url": account.profile_image_url,
                    "is_influencer": account.is_influencer,
                }
                for account in accounts
            ],
        }

    async def discover_creators(self, niche: str | None = None) -> list[dict]:
        query = select(CreatorProfile).where(CreatorProfile.is_public.is_(True)).order_by(CreatorProfile.display_name)
        if niche:
            query = query.where(CreatorProfile.niche.ilike(f"%{niche}%"))
        result = await self.db.execute(query)
        return [await self.creator_profile_data(profile) for profile in result.scalars().all()]

    async def public_creator_profile(self, user_id: int) -> dict | None:
        result = await self.db.execute(select(CreatorProfile).where(CreatorProfile.user_id == user_id, CreatorProfile.is_public.is_(True)))
        profile = result.scalar_one_or_none()
        return await self.creator_profile_data(profile) if profile is not None else None

    async def brand_profile(self, user_id: int) -> BrandProfile | None:
        result = await self.db.execute(select(BrandProfile).where(BrandProfile.user_id == user_id))
        return result.scalar_one_or_none()

    async def save_brand_profile(self, user_id: int, values: BrandProfileCreate | BrandProfileUpdate) -> BrandProfile:
        profile = await self.brand_profile(user_id)
        data = values.model_dump(exclude_unset=True)
        if profile is None:
            profile = BrandProfile(user_id=user_id, **data)
            self.db.add(profile)
        else:
            for key, value in data.items():
                setattr(profile, key, value)
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def _owned_targets(self, user_id: int, account_ids: list[int]) -> list[SocialAccount]:
        if not account_ids:
            return []
        result = await self.db.execute(select(SocialAccount).where(SocialAccount.id.in_(account_ids), SocialAccount.user_id == user_id, SocialAccount.is_active.is_(True)))
        accounts = list(result.scalars().all())
        if len(accounts) != len(account_ids):
            raise ValueError("One or more social accounts were not found")
        platform_service = PlatformService(self.settings)
        for account in accounts:
            platform_service.require_enabled(account.platform)
        return accounts

    async def _content_response(self, item: ContentItem) -> dict:
        result = await self.db.execute(select(ContentTarget).where(ContentTarget.content_item_id == item.id).order_by(ContentTarget.id))
        return {
            "id": item.id,
            "creator_user_id": item.creator_user_id,
            "caption": item.caption,
            "media_url": item.media_url,
            "status": item.status,
            "scheduled_at": item.scheduled_at,
            "published_at": item.published_at,
            "created_at": item.created_at,
            "targets": list(result.scalars().all()),
        }

    def _validate_schedule(self, scheduled_at: datetime | None, account_ids: list[int]) -> None:
        if scheduled_at is None:
            return
        if assume_india_timezone(scheduled_at) <= now_utc():
            raise ValueError("scheduled_at must be in the future")
        if not account_ids:
            raise ValueError("Scheduled content requires at least one social account")

    async def create_content(self, user_id: int, values: ContentCreate) -> dict:
        if values.scheduled_at is not None:
            values.scheduled_at = assume_india_timezone(values.scheduled_at)
        self._validate_schedule(values.scheduled_at, values.social_account_ids)
        accounts = await self._owned_targets(user_id, values.social_account_ids)
        accounts_by_id = {account.id: account for account in accounts}
        item = ContentItem(creator_user_id=user_id, caption=values.caption, media_url=values.media_url, scheduled_at=values.scheduled_at, status="scheduled" if values.scheduled_at else "draft")
        self.db.add(item)
        await self.db.flush()
        target_content = {target.social_account_id: target for target in values.target_content}
        for account_id in values.social_account_ids:
            override = target_content.get(account_id)
            platform_settings = (
                override.platform_settings
                if override and override.platform_settings
                else values.youtube if accounts_by_id[account_id].platform.value == "youtube" else values.facebook
            )
            self.db.add(
                ContentTarget(
                    content_item_id=item.id,
                    social_account_id=account_id,
                    post_type=override.post_type if override else "video",
                    caption=override.caption if override else None,
                    media_url=override.media_url if override else None,
                    platform_settings=platform_settings,
                )
            )
        await self.db.commit()
        await self.db.refresh(item)
        return await self._content_response(item)

    async def get_content(self, user_id: int, content_id: int) -> ContentItem | None:
        result = await self.db.execute(select(ContentItem).where(ContentItem.id == content_id, ContentItem.creator_user_id == user_id))
        return result.scalar_one_or_none()

    async def update_content(self, user_id: int, content_id: int, values: ContentUpdate) -> dict | None:
        item = await self.get_content(user_id, content_id)
        if item is None:
            return None
        if item.status == "published":
            raise ValueError("Published content cannot be edited")
        data = values.model_dump(exclude_unset=True)
        account_ids = data.pop("social_account_ids", None)
        target_content = data.pop("target_content", None)
        youtube_settings = data.pop("youtube", None)
        facebook_settings = data.pop("facebook", None)
        scheduled_at = data.get("scheduled_at", item.scheduled_at)
        if scheduled_at is not None:
            scheduled_at = assume_india_timezone(scheduled_at)
            data["scheduled_at"] = scheduled_at
        if account_ids is None:
            result = await self.db.execute(select(ContentTarget.social_account_id).where(ContentTarget.content_item_id == item.id))
            account_ids = list(result.scalars().all())
        self._validate_schedule(scheduled_at, account_ids)
        owned_accounts = await self._owned_targets(user_id, account_ids)
        accounts_by_id = {account.id: account for account in owned_accounts}
        if "caption" in data or "media_url" in data:
            caption = data.get("caption", item.caption)
            media_url = data.get("media_url", item.media_url)
            if not (caption or media_url):
                raise ValueError("Provide a caption or media URL")
        if "social_account_ids" in values.model_fields_set:
            await self.db.execute(delete(ContentTarget).where(ContentTarget.content_item_id == item.id))
            target_content_by_account = {
                target["social_account_id"]: target for target in target_content or []
            }
            for account_id in account_ids:
                override = target_content_by_account.get(account_id, {})
                platform = accounts_by_id[account_id].platform.value
                self.db.add(
                    ContentTarget(
                        content_item_id=item.id,
                        social_account_id=account_id,
                        post_type=override.get("post_type", "video"),
                        caption=override.get("caption"),
                        media_url=override.get("media_url"),
                        platform_settings=override.get(
                            "platform_settings",
                            youtube_settings if platform == "youtube" else facebook_settings,
                        ) or {},
                    )
                )
        elif target_content is not None:
            result = await self.db.execute(select(ContentTarget).where(ContentTarget.content_item_id == item.id))
            targets_by_account = {target.social_account_id: target for target in result.scalars().all()}
            for override in target_content:
                target = targets_by_account.get(override["social_account_id"])
                if target is None:
                    raise ValueError("Target content must reference selected social accounts")
                target.caption = override.get("caption")
                target.media_url = override.get("media_url")
                target.post_type = override.get("post_type", "video")
                if "platform_settings" in override:
                    target.platform_settings = override["platform_settings"]
        if youtube_settings is not None or facebook_settings is not None:
            result = await self.db.execute(
                select(ContentTarget, SocialAccount)
                .join(SocialAccount, SocialAccount.id == ContentTarget.social_account_id)
                .where(ContentTarget.content_item_id == item.id)
            )
            for target, account in result.all():
                settings = youtube_settings if account.platform.value == "youtube" else facebook_settings
                if settings is not None:
                    target.platform_settings = settings
        for key, value in data.items():
            setattr(item, key, value)
        item.status = "scheduled" if item.scheduled_at else "draft"
        await self.db.commit()
        await self.db.refresh(item)
        return await self._content_response(item)

    async def publish_content(self, user_id: int, content_id: int) -> dict:
        item = await self.get_content(user_id, content_id)
        if item is None:
            raise LookupError("Content not found")
        if item.status == "published":
            raise ValueError("Published content cannot be published again")
        result = await self.db.execute(
            select(ContentTarget, SocialAccount)
            .join(SocialAccount, SocialAccount.id == ContentTarget.social_account_id)
            .where(ContentTarget.content_item_id == item.id, SocialAccount.user_id == user_id, SocialAccount.is_active.is_(True))
            .order_by(ContentTarget.id)
        )
        targets = list(result.all())
        if not targets:
            raise ValueError("Content must target at least one social account")
        for target, account in targets:
            caption = target.caption if target.caption is not None else item.caption
            media_url = target.media_url or item.media_url
            if target.post_type == "text" and not caption:
                raise ValueError(f"{account.platform.value} text targets must have a caption")
            if target.post_type in {"video", "image"} and not media_url:
                raise ValueError(f"{account.platform.value} {target.post_type} targets must have a media URL")
            if account.platform.value == "youtube" and target.post_type != "video":
                raise ValueError("YouTube only supports video publishing through its public API")

        item.status = "publishing"
        await self.db.commit()
        failures: list[str] = []
        for target, account in targets:
            target.status = "publishing"
            await self.db.commit()
            try:
                token = await self._valid_token(account)
                media_url = target.media_url or item.media_url
                caption = target.caption if target.caption is not None else item.caption
                integration = get_integration(account.platform, self.settings)
                await integration.verify_token_owner(token, account.platform_user_id)
                if target.post_type == "text":
                    published = await integration.publish_text(token, caption or "")
                elif target.post_type == "image":
                    published = await integration.publish_image(token, media_url or "", caption)
                else:
                    title = (caption or "Untitled video")[:100]
                    published = await integration.publish_video(
                        token,
                        media_url or "",
                        title,
                        caption,
                        target.platform_settings,
                    )
            except SocialIntegrationError as exc:
                target.status = "failed"
                failures.append(f"{account.platform.value}: {exc}")
            else:
                target.status = "published"
                target.platform_post_id = published.platform_video_id
                target.published_url = published.url
            await self.db.commit()

        if failures:
            item.status = "failed"
            await self.db.commit()
            raise PlatformAPIError("Publishing failed: " + "; ".join(failures))
        item.status = "published"
        item.published_at = now_utc()
        await self.db.commit()
        return await self._content_response(item)

    async def _valid_token(self, account: SocialAccount) -> str:
        from app.services.social_account_service import SocialAccountService

        return await SocialAccountService(self.db, self.settings).valid_token(account)

    async def list_content(self, user_id: int, status: str | None = None, start: datetime | None = None, end: datetime | None = None) -> list[dict]:
        query = select(ContentItem).where(ContentItem.creator_user_id == user_id).order_by(ContentItem.scheduled_at, ContentItem.created_at.desc())
        if status:
            query = query.where(ContentItem.status == status)
        if start:
            query = query.where(ContentItem.scheduled_at >= start)
        if end:
            query = query.where(ContentItem.scheduled_at <= end)
        result = await self.db.execute(query)
        return [await self._content_response(item) for item in result.scalars().all()]

    async def save_campaign(self, user_id: int, values: CampaignCreate | CampaignUpdate, campaign_id: int | None = None) -> Campaign | None:
        if await self.brand_profile(user_id) is None:
            raise ValueError("Create a brand profile before managing campaigns")
        campaign = None
        if campaign_id is not None:
            result = await self.db.execute(select(Campaign).where(Campaign.id == campaign_id, Campaign.brand_user_id == user_id))
            campaign = result.scalar_one_or_none()
            if campaign is None:
                return None
        data = values.model_dump(exclude_unset=True)
        starts_at = data.get("starts_at", campaign.starts_at if campaign else None)
        ends_at = data.get("ends_at", campaign.ends_at if campaign else None)
        if starts_at and ends_at and ends_at < starts_at:
            raise ValueError("Campaign end must be after its start")
        if campaign is None:
            campaign = Campaign(brand_user_id=user_id, **data)
            self.db.add(campaign)
        else:
            for key, value in data.items():
                setattr(campaign, key, value)
        await self.db.commit()
        await self.db.refresh(campaign)
        return campaign

    async def list_campaigns(self, user_id: int | None = None, open_only: bool = False) -> list[Campaign]:
        query = select(Campaign).order_by(Campaign.created_at.desc())
        if user_id is not None:
            query = query.where(Campaign.brand_user_id == user_id)
        elif open_only:
            query = query.where(Campaign.status == "open")
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_collaboration(self, brand_user_id: int, values: CollaborationCreate) -> CollaborationRequest:
        if await self.brand_profile(brand_user_id) is None:
            raise ValueError("Create a brand profile before inviting creators")
        creator_result = await self.db.execute(select(CreatorProfile).where(CreatorProfile.user_id == values.creator_user_id, CreatorProfile.is_public.is_(True)))
        if creator_result.scalar_one_or_none() is None:
            raise ValueError("Public creator profile not found")
        if values.campaign_id is not None:
            campaign_result = await self.db.execute(select(Campaign).where(Campaign.id == values.campaign_id, Campaign.brand_user_id == brand_user_id))
            if campaign_result.scalar_one_or_none() is None:
                raise ValueError("Campaign not found")
        request = CollaborationRequest(brand_user_id=brand_user_id, creator_user_id=values.creator_user_id, campaign_id=values.campaign_id, message=values.message)
        self.db.add(request)
        await self.db.commit()
        await self.db.refresh(request)
        return request

    async def list_collaborations(self, user_id: int, as_creator: bool) -> list[CollaborationRequest]:
        column = CollaborationRequest.creator_user_id if as_creator else CollaborationRequest.brand_user_id
        result = await self.db.execute(select(CollaborationRequest).where(column == user_id).order_by(CollaborationRequest.created_at.desc()))
        return list(result.scalars().all())

    async def update_collaboration(self, user_id: int, request_id: int, status: str, as_creator: bool) -> CollaborationRequest | None:
        column = CollaborationRequest.creator_user_id if as_creator else CollaborationRequest.brand_user_id
        result = await self.db.execute(select(CollaborationRequest).where(CollaborationRequest.id == request_id, column == user_id))
        request = result.scalar_one_or_none()
        if request is None:
            return None
        if as_creator and (request.status != "pending" or status not in {"accepted", "declined"}):
            raise ValueError("Only pending requests can be accepted or declined")
        if not as_creator and (request.status not in {"accepted", "in_progress"} or status not in {"in_progress", "completed", "cancelled"}):
            raise ValueError("Campaign progress cannot be updated from its current status")
        request.status = status
        await self.db.commit()
        await self.db.refresh(request)
        return request

    async def add_metric_snapshot(self, user_id: int, account_id: int, values: MetricSnapshotCreate) -> AccountMetricSnapshot | None:
        result = await self.db.execute(select(SocialAccount).where(SocialAccount.id == account_id, SocialAccount.user_id == user_id, SocialAccount.is_active.is_(True)))
        if result.scalar_one_or_none() is None:
            return None
        snapshot = AccountMetricSnapshot(social_account_id=account_id, **values.model_dump())
        self.db.add(snapshot)
        await self.db.commit()
        await self.db.refresh(snapshot)
        return snapshot

    async def list_metric_snapshots(self, user_id: int, account_id: int) -> list[AccountMetricSnapshot] | None:
        account_result = await self.db.execute(select(SocialAccount.id).where(SocialAccount.id == account_id, SocialAccount.user_id == user_id, SocialAccount.is_active.is_(True)))
        if account_result.scalar_one_or_none() is None:
            return None
        result = await self.db.execute(select(AccountMetricSnapshot).where(AccountMetricSnapshot.social_account_id == account_id).order_by(AccountMetricSnapshot.recorded_at))
        return list(result.scalars().all())

    async def account_analytics(self, user_id: int, account_id: int) -> dict | None:
        account_result = await self.db.execute(select(SocialAccount).where(SocialAccount.id == account_id, SocialAccount.user_id == user_id, SocialAccount.is_active.is_(True)))
        account = account_result.scalar_one_or_none()
        if account is None:
            return None
        totals = await self.db.execute(select(func.count(SocialVideo.id), func.coalesce(func.sum(SocialVideo.view_count), 0), func.coalesce(func.sum(SocialVideo.like_count), 0), func.coalesce(func.sum(SocialVideo.comment_count), 0)).where(SocialVideo.social_account_id == account_id))
        count, views, likes, comments = totals.one()
        snapshots = await self.list_metric_snapshots(user_id, account_id) or []
        follower_values = [snapshot.follower_count for snapshot in snapshots if snapshot.follower_count is not None]
        return {
            "account_id": account.id,
            "platform": account.platform.value,
            "content_count": count,
            "view_count": views,
            "like_count": likes,
            "comment_count": comments,
            "follower_count": follower_values[-1] if follower_values else None,
            "follower_growth": follower_values[-1] - follower_values[0] if len(follower_values) > 1 else None,
            "snapshots": [
                {
                    "id": snapshot.id,
                    "social_account_id": snapshot.social_account_id,
                    "follower_count": snapshot.follower_count,
                    "view_count": snapshot.view_count,
                    "recorded_at": snapshot.recorded_at,
                }
                for snapshot in snapshots
            ],
        }

    async def overview_analytics(self, user_id: int) -> dict:
        result = await self.db.execute(select(SocialAccount).where(SocialAccount.user_id == user_id, SocialAccount.is_active.is_(True)).order_by(SocialAccount.platform))
        accounts = list(result.scalars().all())
        account_analytics = [await self.account_analytics(user_id, account.id) for account in accounts]
        return {
            "accounts": account_analytics,
            "content_count": sum(item["content_count"] for item in account_analytics if item),
            "view_count": sum(item["view_count"] for item in account_analytics if item),
            "like_count": sum(item["like_count"] for item in account_analytics if item),
            "comment_count": sum(item["comment_count"] for item in account_analytics if item),
        }

    async def public_creator_analytics(self, user_id: int) -> dict | None:
        if await self.public_creator_profile(user_id) is None:
            return None
        return await self.overview_analytics(user_id)

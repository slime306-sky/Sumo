from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.security import create_oauth_state
from app.integrations.base import OAuthError, SocialPlatform
from app.integrations.registry import get_integration
from app.models.social_account import Platform, SocialAccount
from app.services.platform_service import PlatformService


class SocialAccountService:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    def authorization_url(self, user_id: int, platform: Platform) -> str:
        PlatformService(self.settings).require_enabled(platform)
        integration = get_integration(platform, self.settings)
        return integration.get_authorization_url(create_oauth_state(user_id, platform.value))

    async def connect(self, user_id: int, platform: Platform, code: str) -> SocialAccount:
        PlatformService(self.settings).require_enabled(platform)
        integration = get_integration(platform, self.settings)
        token = await integration.exchange_code_for_token(code)
        await integration.verify_permissions(token.access_token)
        profile = await integration.get_profile(token.access_token)
        result = await self.db.execute(select(SocialAccount).where(SocialAccount.user_id == user_id, SocialAccount.platform == platform, SocialAccount.platform_user_id == profile.platform_user_id))
        account = result.scalar_one_or_none()
        if account is None:
            account = SocialAccount(user_id=user_id, platform=platform, platform_user_id=profile.platform_user_id, access_token=token.access_token)
            self.db.add(account)
        account.access_token = token.access_token
        account.refresh_token = token.refresh_token or account.refresh_token
        account.token_expires_at = token.expires_at
        account.platform_username = profile.username
        account.profile_name = profile.name
        account.profile_image_url = profile.image_url
        account.is_active = True
        await self.db.commit()
        await self.db.refresh(account)
        return account

    async def get_account(self, user_id: int, account_id: int) -> SocialAccount | None:
        result = await self.db.execute(select(SocialAccount).where(SocialAccount.id == account_id, SocialAccount.user_id == user_id, SocialAccount.is_active.is_(True)))
        account = result.scalar_one_or_none()
        if account is not None:
            PlatformService(self.settings).require_enabled(account.platform)
        return account

    async def set_influencer(self, user_id: int, account_id: int, is_influencer: bool) -> SocialAccount | None:
        account = await self.get_account(user_id, account_id)
        if account is None:
            return None
        account.is_influencer = is_influencer
        await self.db.commit()
        await self.db.refresh(account)
        return account

    async def disconnect(self, user_id: int, account_id: int) -> bool:
        result = await self.db.execute(
            select(SocialAccount).where(
                SocialAccount.id == account_id,
                SocialAccount.user_id == user_id,
                SocialAccount.is_active.is_(True),
            )
        )
        account = result.scalar_one_or_none()
        if account is None:
            return False
        account.is_active = False
        account.access_token = ""
        account.refresh_token = None
        account.token_expires_at = None
        await self.db.commit()
        return True

    async def list_accounts(self, user_id: int) -> list[SocialAccount]:
        result = await self.db.execute(select(SocialAccount).where(SocialAccount.user_id == user_id, SocialAccount.is_active.is_(True)).order_by(SocialAccount.created_at.desc()))
        return [account for account in result.scalars().all() if PlatformService(self.settings).is_enabled(account.platform)]

    async def valid_token(self, account: SocialAccount) -> str:
        PlatformService(self.settings).require_enabled(account.platform)
        if account.token_expires_at and account.token_expires_at <= datetime.now(timezone.utc):
            if not account.refresh_token:
                raise OAuthError("The social account token has expired")
            integration = get_integration(account.platform, self.settings)
            token = await integration.refresh_access_token(account.refresh_token)
            account.access_token = token.access_token
            account.token_expires_at = token.expires_at
            await self.db.commit()
        return account.access_token

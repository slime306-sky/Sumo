from abc import ABC, abstractmethod
from dataclasses import dataclass
import logging
from datetime import datetime
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import Settings
from app.models.social_account import Platform

logger = logging.getLogger(__name__)


class SocialIntegrationError(Exception):
    pass


class OAuthError(SocialIntegrationError):
    pass


class TokenExpiredError(SocialIntegrationError):
    pass


class RateLimitError(SocialIntegrationError):
    pass


class PlatformAPIError(SocialIntegrationError):
    pass


class UnsupportedPlatformError(SocialIntegrationError):
    pass


@dataclass
class TokenData:
    access_token: str
    refresh_token: str | None = None
    expires_at: datetime | None = None


@dataclass
class ProfileData:
    platform_user_id: str
    username: str | None = None
    name: str | None = None
    image_url: str | None = None


@dataclass
class NormalizedVideo:
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
    raw_data: dict[str, Any] | None = None


@dataclass
class VideoPage:
    items: list[NormalizedVideo]
    next_cursor: str | None = None


class SocialPlatform(ABC):
    platform: Platform

    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self.settings = settings
        self.client = client or httpx.AsyncClient(timeout=settings.request_timeout_seconds)

    @abstractmethod
    def get_authorization_url(self, state: str) -> str:
        raise NotImplementedError

    @abstractmethod
    async def exchange_code_for_token(self, code: str) -> TokenData:
        raise NotImplementedError

    async def refresh_access_token(self, refresh_token: str) -> TokenData:
        raise OAuthError(f"{self.platform.value} does not support token refresh")

    async def verify_permissions(self, access_token: str) -> None:
        return None

    async def verify_token_owner(self, access_token: str, platform_user_id: str) -> None:
        return None

    @abstractmethod
    async def get_profile(self, access_token: str) -> ProfileData:
        raise NotImplementedError

    @abstractmethod
    async def get_videos(self, access_token: str, cursor: str | None = None) -> VideoPage:
        raise NotImplementedError

    async def publish_video(self, access_token: str, media_url: str, title: str, description: str | None = None, settings: dict | None = None) -> NormalizedVideo:
        raise UnsupportedPlatformError(f"{self.platform.value} does not support video publishing")

    async def publish_text(self, access_token: str, message: str) -> NormalizedVideo:
        raise UnsupportedPlatformError(f"{self.platform.value} does not support text publishing")

    async def publish_image(self, access_token: str, media_url: str, caption: str | None = None) -> NormalizedVideo:
        raise UnsupportedPlatformError(f"{self.platform.value} does not support image publishing")

    async def close(self) -> None:
        await self.client.aclose()

    async def _request(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        params = kwargs.get("params")
        if isinstance(params, dict) and "access_token" in params:
            params = dict(params)
            access_token = params.pop("access_token")
            kwargs["params"] = params
            headers = dict(kwargs.get("headers") or {})
            headers["Authorization"] = f"Bearer {access_token}"
            kwargs["headers"] = headers
        response = await self.client.request(method, url, **kwargs)
        if self.platform == Platform.FACEBOOK:
            error = {}
            try:
                error = response.json().get("error", {})
            except (ValueError, AttributeError):
                pass
            logger.info(
                "Facebook Graph API response",
                extra={
                    "method": method,
                    "path": url.split("?", 1)[0],
                    "status_code": response.status_code,
                    "graph_error_code": error.get("code"),
                    "graph_error_message": error.get("message"),
                },
            )
        if response.status_code == 429:
            raise RateLimitError(f"{self.platform.value} rate limit reached")
        if response.status_code >= 400:
            detail = ""
            reason = ""
            try:
                error = response.json().get("error", {})
                detail = error.get("message") or error.get("status") or ""
                reasons = error.get("errors") or []
                if reasons and isinstance(reasons[0], dict):
                    reason = reasons[0].get("reason", "")
            except (ValueError, AttributeError):
                pass
            if reason in {"quotaExceeded", "dailyLimitExceeded", "userRateLimitExceeded", "rateLimitExceeded"}:
                raise RateLimitError(
                    f"{self.platform.value} API quota or rate limit reached"
                    + (f": {detail}" if detail else "")
                )
            suffix = f": {detail}" if detail else ""
            raise PlatformAPIError(f"{self.platform.value} API returned HTTP {response.status_code}{suffix}")
        try:
            return response.json()
        except ValueError as exc:
            raise PlatformAPIError(f"{self.platform.value} returned invalid JSON") from exc


def oauth_url(base_url: str, params: dict[str, str | None]) -> str:
    return f"{base_url}?{urlencode({key: value for key, value in params.items() if value is not None})}"

import logging
from datetime import date, datetime
from typing import Any

from app.integrations.base import NormalizedVideo, PlatformAPIError, ProfileData, SocialPlatform, TokenData, VideoPage, oauth_url
from app.models.social_account import Platform

logger = logging.getLogger(__name__)


class FacebookIntegration(SocialPlatform):
    platform = Platform.FACEBOOK
    required_permissions = ("public_profile", "pages_show_list", "pages_read_engagement", "pages_manage_posts", "read_insights")
    insight_metrics = (
        "page_impressions",
        "page_post_engagements",
        "page_actions_post_reactions_total",
        "page_fans",
        "page_fan_adds",
        "page_fan_removes",
        "page_video_views",
        "page_video_view_time",
    )

    @property
    def graph_url(self) -> str:
        return f"https://graph.facebook.com/{self.settings.facebook_graph_api_version}"

    def get_authorization_url(self, state: str) -> str:
        return oauth_url(
            f"https://www.facebook.com/{self.settings.facebook_graph_api_version}/dialog/oauth",
            {
                "client_id": self.settings.facebook_app_id,
                "redirect_uri": self.settings.facebook_redirect_uri,
                "config_id": self.settings.facebook_config_id,
                "response_type": "code",
                "scope": ",".join(self.required_permissions),
                "auth_type": "rerequest",
                "state": state,
            },
        )

    async def exchange_code_for_token(self, code: str) -> TokenData:
        data = await self._request("GET", f"{self.graph_url}/oauth/access_token", params={"client_id": self.settings.facebook_app_id, "client_secret": self.settings.facebook_app_secret, "redirect_uri": self.settings.facebook_redirect_uri, "code": code})
        return TokenData(data["access_token"])

    async def verify_permissions(self, access_token: str) -> None:
        data = await self._request("GET", f"{self.graph_url}/me/permissions", params={"access_token": access_token})
        granted = {item.get("permission") for item in data.get("data", []) if item.get("status") == "granted"}
        missing = [permission for permission in self.required_permissions if permission not in granted]
        logger.info("Facebook OAuth permissions verified", extra={"granted_permissions": sorted(granted), "missing_permissions": missing})
        if missing:
            raise PlatformAPIError("Facebook did not grant required permissions: " + ", ".join(missing) + ". Reconnect Facebook and approve all requested permissions.")

    async def verify_token_owner(self, access_token: str, platform_user_id: str) -> None:
        profile = await self.get_profile(access_token)
        if profile.platform_user_id != platform_user_id:
            raise PlatformAPIError("Facebook token belongs to a different account than the connected SUMO account")

    async def get_profile(self, access_token: str) -> ProfileData:
        data = await self._request("GET", f"{self.graph_url}/me", params={"fields": "id,name,picture", "access_token": access_token})
        return ProfileData(data["id"], None, data.get("name"), data.get("picture", {}).get("data", {}).get("url"))

    async def managed_page(self, access_token: str) -> dict:
        url = f"{self.graph_url}/me/accounts"
        params: dict[str, str] = {"fields": "id,name,access_token", "limit": "100", "access_token": access_token}
        pages: list[dict] = []
        while url:
            data = await self._request("GET", url, params=params)
            batch = data.get("data")
            if not isinstance(batch, list):
                raise PlatformAPIError("Facebook managed Page response did not contain a valid data list")
            pages.extend(page for page in batch if isinstance(page, dict))
            url = data.get("paging", {}).get("next")
            params = {"access_token": access_token} if url else {}
        valid_pages = [page for page in pages if page.get("id") and page.get("access_token")]
        logger.info(
            "Facebook managed Pages lookup completed",
            extra={
                "page_count": len(pages),
                "valid_page_count": len(valid_pages),
                "missing_page_id_count": sum(1 for page in pages if not page.get("id")),
                "missing_page_token_count": sum(1 for page in pages if page.get("id") and not page.get("access_token")),
            },
        )
        if not pages:
            raise PlatformAPIError("Facebook returned no managed Pages. Confirm this Facebook user has sufficient access to at least one Page.")
        if not valid_pages:
            raise PlatformAPIError("Facebook returned managed Pages, but none included both a Page ID and Page Access Token. Confirm this user has sufficient Page access and that the token can retrieve Page tokens.")
        return valid_pages[0]

    async def get_videos(self, access_token: str, cursor: str | None = None) -> VideoPage:
        params = {"fields": "id,message,permalink_url,created_time,thumbnails,description,views,likes.summary(true),comments.summary(true)", "limit": "100", "access_token": access_token}
        if cursor:
            params["after"] = cursor
        data = await self._request("GET", f"{self.graph_url}/me/videos", params=params)
        items = [NormalizedVideo(item["id"], item.get("message"), item.get("description"), item.get("permalink_url"), _thumbnail(item), _parse_datetime(item.get("created_time")), None, item.get("views"), _summary(item.get("likes")), _summary(item.get("comments")), item) for item in data.get("data", [])]
        return VideoPage(items, (data.get("paging", {}).get("cursors") or {}).get("after"))

    async def get_analytics(self, access_token: str, start_date: date, end_date: date) -> dict[str, Any]:
        if start_date > end_date:
            raise ValueError("Facebook analytics start date must be before or equal to end date")

        page = await self.managed_page(access_token)
        data = await self._request(
            "GET",
            f"{self.graph_url}/{page['id']}/insights",
            params={
                "metric": ",".join(self.insight_metrics),
                "period": "day",
                "since": start_date.isoformat(),
                "until": end_date.isoformat(),
                "access_token": page["access_token"],
            },
        )
        return {
            "page": {"id": page["id"], "name": page.get("name")},
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "insights": data.get("data", []),
        }

    async def publish_video(self, access_token: str, media_url: str, title: str, description: str | None = None) -> NormalizedVideo:
        page = await self.managed_page(access_token)
        data = await self._request("POST", f"{self.graph_url}/{page['id']}/videos", data={"file_url": media_url, "title": title, "description": description or ""}, params={"access_token": page["access_token"]})
        video_id = data.get("id")
        if not video_id:
            raise PlatformAPIError("Facebook upload response did not include a video ID")
        return NormalizedVideo(video_id, title, description, f"https://www.facebook.com/{video_id}", raw_data=data)

    async def publish_text(self, access_token: str, message: str) -> NormalizedVideo:
        page = await self.managed_page(access_token)
        data = await self._request("POST", f"{self.graph_url}/{page['id']}/feed", data={"message": message}, params={"access_token": page["access_token"]})
        post_id = data.get("id")
        if not post_id:
            raise PlatformAPIError("Facebook text post response did not include a post ID")
        return NormalizedVideo(post_id, message, None, f"https://www.facebook.com/{post_id}", raw_data=data)

    async def publish_image(self, access_token: str, media_url: str, caption: str | None = None) -> NormalizedVideo:
        page = await self.managed_page(access_token)
        data = await self._request("POST", f"{self.graph_url}/{page['id']}/photos", data={"url": media_url, "caption": caption or ""}, params={"access_token": page["access_token"]})
        post_id = data.get("post_id") or data.get("id")
        if not post_id:
            raise PlatformAPIError("Facebook image post response did not include a post ID")
        return NormalizedVideo(post_id, caption, caption, f"https://www.facebook.com/{post_id}", raw_data=data)


def _summary(value: dict | None) -> int | None:
    return (value or {}).get("summary", {}).get("total_count")


def _thumbnail(item: dict) -> str | None:
    return ((item.get("thumbnails", {}).get("data") or [{}])[0]).get("uri")


def _parse_datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None

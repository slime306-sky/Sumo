from datetime import datetime

from app.integrations.base import NormalizedVideo, PlatformAPIError, ProfileData, SocialPlatform, TokenData, VideoPage, oauth_url
from app.models.social_account import Platform


class FacebookIntegration(SocialPlatform):
    platform = Platform.FACEBOOK
    graph_url = "https://graph.facebook.com/v23.0"

    def get_authorization_url(self, state: str) -> str:
        return oauth_url("https://www.facebook.com/v23.0/dialog/oauth", {"client_id": self.settings.facebook_app_id, "redirect_uri": self.settings.facebook_redirect_uri, "config_id": self.settings.facebook_config_id, "response_type": "code", "scope": "pages_show_list,pages_manage_posts,pages_read_engagement", "state": state})

    async def exchange_code_for_token(self, code: str) -> TokenData:
        data = await self._request("GET", f"{self.graph_url}/oauth/access_token", params={"client_id": self.settings.facebook_app_id, "client_secret": self.settings.facebook_app_secret, "redirect_uri": self.settings.facebook_redirect_uri, "code": code})
        return TokenData(data["access_token"])

    async def get_profile(self, access_token: str) -> ProfileData:
        data = await self._request("GET", f"{self.graph_url}/me", params={"fields": "id,name,picture", "access_token": access_token})
        return ProfileData(data["id"], None, data.get("name"), data.get("picture", {}).get("data", {}).get("url"))

    async def get_videos(self, access_token: str, cursor: str | None = None) -> VideoPage:
        params = {"fields": "id,message,permalink_url,created_time,thumbnails,description,views,likes.summary(true),comments.summary(true)", "limit": "100", "access_token": access_token}
        if cursor: params["after"] = cursor
        data = await self._request("GET", f"{self.graph_url}/me/videos", params=params)
        items = [NormalizedVideo(item["id"], item.get("message"), item.get("description"), item.get("permalink_url"), _thumbnail(item), _parse_datetime(item.get("created_time")), None, item.get("views"), _summary(item.get("likes")), _summary(item.get("comments")), item) for item in data.get("data", [])]
        return VideoPage(items, (data.get("paging", {}).get("cursors") or {}).get("after"))

    async def publish_video(self, access_token: str, media_url: str, title: str, description: str | None = None) -> NormalizedVideo:
        pages = await self._request("GET", f"{self.graph_url}/me/accounts", params={"fields": "id,access_token", "access_token": access_token})
        page = (pages.get("data") or [None])[0]
        if not page or not page.get("id") or not page.get("access_token"):
            raise PlatformAPIError("Facebook publishing requires a managed Page")
        data = await self._request("POST", f"{self.graph_url}/{page['id']}/videos", data={"file_url": media_url, "title": title, "description": description or ""}, headers={"Authorization": f"Bearer {page['access_token']}"})
        video_id = data.get("id")
        if not video_id:
            raise PlatformAPIError("Facebook upload response did not include a video ID")
        return NormalizedVideo(video_id, title, description, f"https://www.facebook.com/{video_id}", raw_data=data)


def _summary(value: dict | None) -> int | None:
    return (value or {}).get("summary", {}).get("total_count")


def _thumbnail(item: dict) -> str | None:
    return ((item.get("thumbnails", {}).get("data") or [{}])[0]).get("uri")


def _parse_datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None

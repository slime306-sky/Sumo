from datetime import datetime

from app.integrations.base import NormalizedVideo, PlatformAPIError, ProfileData, SocialPlatform, TokenData, VideoPage, oauth_url
from app.models.social_account import Platform


class YouTubeIntegration(SocialPlatform):
    platform = Platform.YOUTUBE
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
    token_url = "https://oauth2.googleapis.com/token"
    api_url = "https://www.googleapis.com/youtube/v3"

    def get_authorization_url(self, state: str) -> str:
        return oauth_url(self.auth_url, {"client_id": self.settings.youtube_client_id, "redirect_uri": self.settings.youtube_redirect_uri, "response_type": "code", "scope": "https://www.googleapis.com/auth/youtube.readonly", "access_type": "offline", "prompt": "consent", "state": state})

    async def exchange_code_for_token(self, code: str) -> TokenData:
        data = await self._request("POST", self.token_url, data={"code": code, "client_id": self.settings.youtube_client_id, "client_secret": self.settings.youtube_client_secret, "redirect_uri": self.settings.youtube_redirect_uri, "grant_type": "authorization_code"})
        return TokenData(data["access_token"], data.get("refresh_token"))

    async def refresh_access_token(self, refresh_token: str) -> TokenData:
        data = await self._request("POST", self.token_url, data={"refresh_token": refresh_token, "client_id": self.settings.youtube_client_id, "client_secret": self.settings.youtube_client_secret, "grant_type": "refresh_token"})
        return TokenData(data["access_token"], refresh_token)

    async def get_profile(self, access_token: str) -> ProfileData:
        data = await self._request("GET", f"{self.api_url}/channels", params={"part": "snippet", "mine": "true", "access_token": access_token})
        item = (data.get("items") or [None])[0]
        if not item:
            raise PlatformAPIError("YouTube channel was not found")
        snippet = item.get("snippet", {})
        return ProfileData(item["id"], snippet.get("customUrl"), snippet.get("title"), snippet.get("thumbnails", {}).get("default", {}).get("url"))

    async def get_videos(self, access_token: str, cursor: str | None = None) -> VideoPage:
        params = {"part": "snippet,contentDetails,statistics", "mine": "true", "maxResults": "50", "access_token": access_token}
        if cursor:
            params["pageToken"] = cursor
        search = await self._request("GET", f"{self.api_url}/search", params={"part": "id", "forMine": "true", "type": "video", "maxResults": "50", "access_token": access_token, **({"pageToken": cursor} if cursor else {})})
        ids = [item.get("id", {}).get("videoId") for item in search.get("items", [])]
        if not ids:
            return VideoPage([])
        data = await self._request("GET", f"{self.api_url}/videos", params={"part": "snippet,contentDetails,statistics", "id": ",".join(ids), "access_token": access_token})
        items = []
        for item in data.get("items", []):
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            content = item.get("contentDetails", {})
            items.append(NormalizedVideo(item["id"], snippet.get("title"), snippet.get("description"), f"https://www.youtube.com/watch?v={item['id']}", snippet.get("thumbnails", {}).get("high", {}).get("url"), _parse_datetime(snippet.get("publishedAt")), _duration_seconds(content.get("duration")), _integer(stats.get("viewCount")), _integer(stats.get("likeCount")), _integer(stats.get("commentCount")), item))
        return VideoPage(items, search.get("nextPageToken"))


def _integer(value: str | None) -> int | None:
    return int(value) if value is not None else None


def _parse_datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def _duration_seconds(value: str | None) -> int | None:
    if not value or not value.startswith("PT"):
        return None
    value = value[2:]
    hours = minutes = seconds = 0
    number = ""
    for char in value:
        if char.isdigit():
            number += char
        elif number:
            if char == "H": hours = int(number)
            elif char == "M": minutes = int(number)
            elif char == "S": seconds = int(number)
            number = ""
    return hours * 3600 + minutes * 60 + seconds

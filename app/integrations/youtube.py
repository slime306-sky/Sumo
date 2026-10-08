from datetime import datetime
from calendar import monthrange
from datetime import date, timedelta
from typing import Any

from app.integrations.base import NormalizedVideo, PlatformAPIError, ProfileData, SocialPlatform, TokenData, VideoPage, oauth_url
from app.models.social_account import Platform


class YouTubeIntegration(SocialPlatform):
    platform = Platform.YOUTUBE
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
    token_url = "https://oauth2.googleapis.com/token"
    api_url = "https://www.googleapis.com/youtube/v3"

    def get_authorization_url(self, state: str) -> str:
        return oauth_url(self.auth_url, {"client_id": self.settings.youtube_client_id, "redirect_uri": self.settings.youtube_redirect_uri, "response_type": "code", "scope": "https://www.googleapis.com/auth/youtube.readonly https://www.googleapis.com/auth/yt-analytics.readonly", "access_type": "offline", "prompt": "consent", "state": state})

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

    async def get_analytics(self, access_token: str, start_date: date, end_date: date) -> dict[str, Any]:
        if type(start_date) is not date or type(end_date) is not date:
            raise TypeError("YouTube analytics dates must be date instances")
        if start_date > end_date:
            raise ValueError("YouTube analytics start date must be before or equal to end date")
        monthly_start = start_date.replace(day=1)
        monthly_end = end_date.replace(day=monthrange(end_date.year, end_date.month)[1])
        latest_available_date = date.today() - timedelta(days=1)
        if monthly_end > latest_available_date:
            monthly_end = end_date.replace(day=1) - timedelta(days=1)
            monthly_start = monthly_end.replace(day=1)
        common = {
            "ids": "channel==MINE",
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "access_token": access_token,
        }
        monthly_range = {
            "ids": "channel==MINE",
            "startDate": monthly_start.isoformat(),
            "endDate": monthly_end.isoformat(),
            "access_token": access_token,
        }
        summary = await self._report(access_token, common, "views,likes,comments,shares,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained,subscribersLost")
        daily = await self._report(access_token, common, "views,likes,comments,shares,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained,subscribersLost", "day")
        monthly = await self._report(access_token, monthly_range, "views,likes,comments,shares,estimatedMinutesWatched,subscribersGained,subscribersLost", "month")
        traffic_sources = await self._report(access_token, common, "views,estimatedMinutesWatched", "insightTrafficSourceType")
        geography = await self._report(access_token, common, "views,estimatedMinutesWatched", "country")
        playback_location = await self._report(access_token, common, "views,estimatedMinutesWatched", "insightPlaybackLocationType")
        age_gender = await self._report(access_token, common, "viewerPercentage", "ageGroup,gender")
        return {
            "start_date": start_date,
            "end_date": end_date,
            "summary": summary,
            "daily": daily,
            "monthly": monthly,
            "traffic_sources": traffic_sources,
            "geography": geography,
            "playback_location": playback_location,
            "age_gender": age_gender,
        }

    async def _report(self, access_token: str, common: dict[str, str], metrics: str, dimensions: str | None = None) -> list[dict[str, Any]]:
        params = {**common, "metrics": metrics}
        if dimensions:
            params["dimensions"] = dimensions
            params["sort"] = dimensions
        data = await self._request("GET", "https://youtubeanalytics.googleapis.com/v2/reports", params=params)
        headers = [column["name"] for column in data.get("columnHeaders", [])]
        return [dict(zip(headers, row, strict=True)) for row in data.get("rows", [])]


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

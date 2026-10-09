from datetime import date

import pytest
from fastapi import HTTPException

from app.api.v1.analytics import _youtube_date_range
from app.core.config import Settings
from app.integrations.base import PlatformAPIError, RateLimitError
from app.integrations.youtube import YouTubeIntegration


class FakeResponse:
    def __init__(self, payload=None, status_code=200):
        self.payload = payload or {"columnHeaders": [], "rows": []}
        self.status_code = status_code

    def json(self):
        return self.payload


class RecordingClient:
    def __init__(self):
        self.requests = []

    async def request(self, method, url, **kwargs):
        self.requests.append((method, url, kwargs))
        return FakeResponse()


class FailingAnalyticsClient(RecordingClient):
    async def request(self, method, url, **kwargs):
        self.requests.append((method, url, kwargs))
        if kwargs["params"].get("dimensions") == "country":
            return FakeResponse({"error": {"message": "Dimension unavailable"}}, status_code=400)
        return FakeResponse()


@pytest.mark.asyncio
async def test_youtube_analytics_preserves_same_day_dates():
    client = RecordingClient()
    integration = YouTubeIntegration(Settings(), client=client)

    await integration.get_analytics("secret-token", date(2026, 10, 8), date(2026, 10, 8))

    normal_params = client.requests[0][2]["params"]
    assert normal_params["startDate"] == "2026-10-08"
    assert normal_params["endDate"] == "2026-10-08"
    assert "access_token" not in normal_params
    assert client.requests[0][2]["headers"] == {"Authorization": "Bearer secret-token"}


@pytest.mark.asyncio
async def test_youtube_analytics_preserves_requested_daily_range():
    client = RecordingClient()
    integration = YouTubeIntegration(Settings(), client=client)

    await integration.get_analytics("secret-token", date(2026, 9, 10), date(2026, 10, 8))

    normal_params = client.requests[0][2]["params"]
    daily_params = client.requests[1][2]["params"]
    assert normal_params["startDate"] == "2026-09-10"
    assert normal_params["endDate"] == "2026-10-08"
    assert daily_params["startDate"] == "2026-09-10"
    assert daily_params["endDate"] == "2026-10-08"


@pytest.mark.asyncio
async def test_youtube_monthly_analytics_uses_month_boundaries():
    client = RecordingClient()
    integration = YouTubeIntegration(Settings(), client=client)

    await integration.get_analytics("secret-token", date(2026, 9, 10), date(2026, 10, 8))

    monthly_params = client.requests[2][2]["params"]
    assert monthly_params["dimensions"] == "month"
    assert monthly_params["startDate"] == "2026-09-01"
    assert monthly_params["endDate"] == "2026-10-01"


def test_youtube_date_range_rejects_reversed_dates():
    with pytest.raises(HTTPException) as error:
        _youtube_date_range(date(2026, 10, 9), date(2026, 10, 8))

    assert error.value.status_code == 422


def test_youtube_date_range_rejects_today_as_end_date():
    with pytest.raises(HTTPException) as error:
        _youtube_date_range(date.today(), date.today())

    assert error.value.status_code == 422


@pytest.mark.asyncio
async def test_youtube_analytics_keeps_core_data_when_optional_report_fails():
    client = FailingAnalyticsClient()
    integration = YouTubeIntegration(Settings(), client=client)

    result = await integration.get_analytics("secret-token", date(2026, 10, 1), date(2026, 10, 8))

    assert result["summary"] == []
    assert result["daily"] == []
    assert result["geography"] == []


@pytest.mark.asyncio
async def test_youtube_quota_error_is_reported_as_rate_limit():
    class QuotaClient:
        async def request(self, method, url, **kwargs):
            return FakeResponse(
                {
                    "error": {
                        "message": "Quota exceeded",
                        "errors": [{"reason": "quotaExceeded"}],
                    }
                },
                status_code=403,
            )

    integration = YouTubeIntegration(Settings(), client=QuotaClient())

    with pytest.raises(RateLimitError, match="quota or rate limit"):
        await integration._request(
            "GET",
            "https://youtubeanalytics.googleapis.com/v2/reports",
            params={"access_token": "secret-token"},
        )

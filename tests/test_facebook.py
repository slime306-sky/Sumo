import pytest
from urllib.parse import parse_qs, urlparse

from app.core.config import Settings
from app.integrations.facebook import FacebookIntegration
from app.integrations.base import PlatformAPIError


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def json(self):
        return self.payload


class RecordingClient:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []

    async def request(self, method, url, **kwargs):
        self.requests.append((method, url, kwargs))
        return next(self.responses)


def test_facebook_authorization_url_requests_page_permissions():
    integration = FacebookIntegration(Settings(facebook_app_id="app-id", facebook_redirect_uri="http://localhost/callback"))

    query = parse_qs(urlparse(integration.get_authorization_url("signed-state")).query)

    assert query["client_id"] == ["app-id"]
    assert query["redirect_uri"] == ["http://localhost/callback"]
    assert query["scope"][0].split(",") == [
        "public_profile",
        "pages_show_list",
        "pages_read_engagement",
        "pages_manage_posts",
    ]
    assert query["state"] == ["signed-state"]


@pytest.mark.asyncio
async def test_verify_permissions_reports_missing_grants():
    client = RecordingClient([FakeResponse({"data": [
        {"permission": "public_profile", "status": "granted"},
        {"permission": "pages_show_list", "status": "granted"},
    ]})])
    integration = FacebookIntegration(Settings(), client=client)

    with pytest.raises(PlatformAPIError, match="pages_read_engagement, pages_manage_posts"):
        await integration.verify_permissions("user-token")


@pytest.mark.asyncio
async def test_managed_page_paginates_and_uses_page_token_for_publish():
    client = RecordingClient(
        [
            FakeResponse({"data": [{"id": "page-without-token"}], "paging": {"next": "https://graph.facebook.com/v23.0/me/accounts?after=next"}}),
            FakeResponse({"data": [{"id": "page-456", "access_token": "page-token"}]}),
            FakeResponse({"id": "post-789"}),
        ]
    )
    integration = FacebookIntegration(Settings(), client=client)

    published = await integration.publish_text("user-token", "Hello Page")

    assert published.platform_video_id == "post-789"
    method, url, request = client.requests[2]
    assert method == "POST"
    assert url.endswith("/page-456/feed")
    assert "Authorization" in request["headers"]
    assert request["headers"]["Authorization"] != "user-token"
    assert "access_token" not in request.get("params", {})
    assert request["data"] == {"message": "Hello Page"}


@pytest.mark.asyncio
async def test_managed_page_requires_a_page_token():
    client = RecordingClient([FakeResponse({"data": [{"id": "page-123"}]})])
    integration = FacebookIntegration(Settings(), client=client)

    with pytest.raises(PlatformAPIError, match="no managed Page"):
        await integration.managed_page("user-token")


@pytest.mark.asyncio
async def test_publish_video_uploads_to_a_managed_page():
    client = RecordingClient(
        [
            FakeResponse({"data": [{"id": "page-123", "access_token": "page-token"}]}),
            FakeResponse({"id": "video-456"}),
        ]
    )
    integration = FacebookIntegration(Settings(), client=client)

    published = await integration.publish_video(
        "user-token",
        "https://cdn.example.com/video.mp4",
        "Launch video",
        "Watch this",
    )

    assert published.platform_video_id == "video-456"
    assert published.url == "https://www.facebook.com/video-456"
    assert client.requests[0][2]["params"]["fields"] == "id,name,access_token"
    method, url, request = client.requests[1]
    assert method == "POST"
    assert url.endswith("/page-123/videos")
    assert request["headers"] == {"Authorization": "Bearer page-token"}
    assert request["data"] == {
        "file_url": "https://cdn.example.com/video.mp4",
        "title": "Launch video",
        "description": "Watch this",
    }


@pytest.mark.asyncio
async def test_publish_video_requires_a_managed_page():
    client = RecordingClient([FakeResponse({"data": []})])
    integration = FacebookIntegration(Settings(), client=client)

    with pytest.raises(PlatformAPIError, match="no managed Page with a Page access token"):
        await integration.publish_video("user-token", "https://cdn.example.com/video.mp4", "Launch video")


@pytest.mark.asyncio
async def test_publish_video_skips_pages_without_page_tokens():
    client = RecordingClient(
        [
            FakeResponse(
                {
                    "data": [
                        {"id": "page-without-token", "name": "Unavailable Page"},
                        {"name": "Missing ID", "access_token": "page-token"},
                    ]
                }
            )
        ]
    )
    integration = FacebookIntegration(Settings(), client=client)

    with pytest.raises(PlatformAPIError, match="reconnect Facebook"):
        await integration.publish_video("user-token", "https://cdn.example.com/video.mp4", "Launch video")

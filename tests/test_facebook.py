import pytest

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

    with pytest.raises(PlatformAPIError, match="managed Page"):
        await integration.publish_video("user-token", "https://cdn.example.com/video.mp4", "Launch video")

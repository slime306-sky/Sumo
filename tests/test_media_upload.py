from io import BytesIO

import pytest
from fastapi import UploadFile

from app.core.config import Settings
from app.services.media_upload_service import MediaUploadError, MediaUploadService


def settings() -> Settings:
    return Settings(
        cloudinary_cloud_name="cloud",
        cloudinary_api_key="key",
        cloudinary_api_secret="secret",
    )


@pytest.mark.asyncio
async def test_upload_video_returns_cloudinary_media_url(monkeypatch):
    captured = {}

    def upload(file, **options):
        captured["file"] = file
        captured["options"] = options
        return {
            "secure_url": "https://res.cloudinary.com/cloud/video/upload/v1/sumo/videos/4/abc.mp4",
            "public_id": "sumo/videos/4/abc",
            "resource_type": "video",
            "format": "mp4",
            "bytes": 4,
            "duration": 1.5,
        }

    monkeypatch.setattr("app.services.media_upload_service.cloudinary.uploader.upload", upload)
    file = UploadFile(filename="clip.mp4", file=BytesIO(b"data"), headers={"content-type": "video/mp4"})

    result = await MediaUploadService(settings()).upload_video(file, 4)

    assert result["media_url"].startswith("https://res.cloudinary.com/")
    assert result["original_filename"] == "clip.mp4"
    assert captured["file"].read() == b"data"
    assert captured["options"]["resource_type"] == "video"
    assert captured["options"]["public_id"].startswith("sumo/videos/4/")


@pytest.mark.asyncio
async def test_upload_video_rejects_non_video_file():
    file = UploadFile(filename="notes.txt", file=BytesIO(b"data"), headers={"content-type": "text/plain"})

    with pytest.raises(MediaUploadError, match="Only video files"):
        await MediaUploadService(settings()).upload_video(file, 4)


@pytest.mark.asyncio
async def test_upload_profile_image_uploads_file_to_cloudinary(monkeypatch):
    captured = {}

    def upload(file, **options):
        captured["file"] = file
        captured["options"] = options
        return {
            "secure_url": "https://res.cloudinary.com/cloud/image/upload/v1/sumo/profile-pictures/4/abc.jpg",
            "public_id": "sumo/profile-pictures/4/abc",
            "resource_type": "image",
            "format": "jpg",
            "bytes": 4,
        }

    monkeypatch.setattr("app.services.media_upload_service.cloudinary.uploader.upload", upload)
    file = UploadFile(filename="profile.jpg", file=BytesIO(b"data"), headers={"content-type": "image/jpeg"})

    result = await MediaUploadService(settings()).upload_profile_image(file, 4)

    assert result["profile_pic"].startswith("https://res.cloudinary.com/")
    assert result["original_filename"] == "profile.jpg"
    assert captured["file"].read() == b"data"
    assert captured["options"]["resource_type"] == "image"
    assert captured["options"]["public_id"].startswith("sumo/profile-pictures/4/")


@pytest.mark.asyncio
async def test_upload_profile_image_rejects_non_image_file():
    file = UploadFile(filename="notes.txt", file=BytesIO(b"data"), headers={"content-type": "text/plain"})

    with pytest.raises(MediaUploadError, match="Only image files"):
        await MediaUploadService(settings()).upload_profile_image(file, 4)

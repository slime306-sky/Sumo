from pathlib import Path
from uuid import uuid4

import cloudinary
import cloudinary.uploader
from cloudinary.exceptions import Error as CloudinaryError
from fastapi import UploadFile
from starlette.concurrency import run_in_threadpool

from app.core.config import Settings


class MediaUploadError(Exception):
    pass


class MediaUploadService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        missing = [
            name
            for name, value in (
                ("CLOUDINARY_CLOUD_NAME", settings.cloudinary_cloud_name),
                ("CLOUDINARY_API_KEY", settings.cloudinary_api_key),
                ("CLOUDINARY_API_SECRET", settings.cloudinary_api_secret),
            )
            if not value
        ]
        if missing:
            raise MediaUploadError(f"Cloudinary is not configured: missing {', '.join(missing)}")
        cloudinary.config(
            cloud_name=settings.cloudinary_cloud_name,
            api_key=settings.cloudinary_api_key,
            api_secret=settings.cloudinary_api_secret,
            secure=True,
        )

    async def upload_video(self, file: UploadFile, user_id: int) -> dict:
        if not file.filename:
            raise MediaUploadError("A video filename is required")
        if not file.content_type or not file.content_type.startswith("video/"):
            raise MediaUploadError("Only video files are supported")

        file_size = await self._file_size(file)
        if file_size > self.settings.max_video_upload_bytes:
            limit_mb = self.settings.max_video_upload_bytes // (1024 * 1024)
            raise MediaUploadError(f"Video exceeds the {limit_mb} MB upload limit")

        public_id = f"{self.settings.cloudinary_upload_folder.strip('/')}/{user_id}/{uuid4().hex}"
        try:
            result = await run_in_threadpool(
                cloudinary.uploader.upload,
                file.file,
                resource_type="video",
                public_id=public_id,
                overwrite=False,
                use_filename=False,
                unique_filename=False,
            )
        except CloudinaryError as exc:
            raise MediaUploadError("Cloudinary video upload failed") from exc

        return {
            "media_url": result["secure_url"],
            "public_id": result["public_id"],
            "resource_type": result.get("resource_type", "video"),
            "format": result.get("format"),
            "bytes": result.get("bytes", file_size),
            "duration": result.get("duration"),
            "original_filename": Path(file.filename).name,
        }

    @staticmethod
    async def _file_size(file: UploadFile) -> int:
        size = await run_in_threadpool(_file_size, file.file)
        await file.seek(0)
        return size


def _file_size(file) -> int:
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    return size

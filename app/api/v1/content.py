import json
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.api.v1.social_accounts import current_user_id
from app.integrations.base import SocialIntegrationError
from app.schemas.creator_platform import ContentCreate, ContentResponse, ContentUpdate, VideoUploadResponse
from app.services.creator_platform_service import CreatorPlatformService
from app.services.media_upload_service import MediaUploadError, MediaUploadService

router = APIRouter(prefix="/content", tags=["content management"])


@router.post("/upload", response_model=VideoUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_video(
    file: UploadFile = File(...),
    user_id: int = Depends(current_user_id),
) -> dict:
    try:
        return await MediaUploadService(get_settings()).upload_video(file, user_id)
    except MediaUploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        await file.close()


@router.post("/upload-and-publish", response_model=ContentResponse, status_code=status.HTTP_201_CREATED)
async def upload_and_publish(
    file: UploadFile = File(...),
    caption: str | None = Form(default=None),
    social_account_ids: str = Form(...),
    scheduled_at: str | None = Form(default=None),
    youtube: str | None = Form(default=None),
    facebook: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(current_user_id),
) -> dict:
    """Upload one video to Cloudinary and publish it to selected accounts."""
    try:
        upload = await MediaUploadService(get_settings()).upload_video(file, user_id)
        try:
            account_ids = _form_int_list(social_account_ids)
            values = ContentCreate.model_validate(
                {
                    "caption": caption,
                    "media_url": upload["media_url"],
                    "social_account_ids": account_ids,
                    "scheduled_at": scheduled_at,
                    "youtube": _form_object(youtube),
                    "facebook": _form_object(facebook),
                }
            )
            service = CreatorPlatformService(db, get_settings())
            content = await service.create_content(user_id, values)
            if values.scheduled_at is not None:
                return content
            return await service.publish_content(user_id, content["id"])
        except (ValueError, SocialIntegrationError) as exc:
            raise HTTPException(
                status_code=502 if isinstance(exc, SocialIntegrationError) else 400,
                detail=str(exc),
            ) from exc
    except MediaUploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        await file.close()


def _form_int_list(value: str) -> list[int]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        parsed = [part.strip() for part in value.split(",") if part.strip()]
    if not isinstance(parsed, list):
        raise ValueError("social_account_ids must be a JSON array of account IDs")
    try:
        account_ids = [int(item) for item in parsed]
    except (TypeError, ValueError) as exc:
        raise ValueError("social_account_ids must contain only integer account IDs") from exc
    return account_ids


def _form_object(value: str | None) -> dict:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError("Platform settings must be valid JSON objects") from exc
    if not isinstance(parsed, dict):
        raise ValueError("Platform settings must be JSON objects")
    return parsed


@router.post("", response_model=ContentResponse, status_code=status.HTTP_201_CREATED)
async def create_content(values: ContentCreate, db: AsyncSession = Depends(get_db), user_id: int = Depends(current_user_id)) -> dict:
    try:
        return await CreatorPlatformService(db, get_settings()).create_content(user_id, values)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/calendar", response_model=list[ContentResponse])
async def content_calendar(start: datetime = Query(...), end: datetime = Query(...), db: AsyncSession = Depends(get_db), user_id: int = Depends(current_user_id)) -> list[dict]:
    if start >= end:
        raise HTTPException(status_code=400, detail="Calendar end must be after its start")
    return await CreatorPlatformService(db, get_settings()).list_content(user_id, status="scheduled", start=start, end=end)


@router.get("/history", response_model=list[ContentResponse])
async def publishing_history(db: AsyncSession = Depends(get_db), user_id: int = Depends(current_user_id)) -> list[dict]:
    return await CreatorPlatformService(db, get_settings()).list_content(user_id, status="published")


@router.get("", response_model=list[ContentResponse])
async def list_content(status_filter: str | None = Query(default=None, alias="status"), db: AsyncSession = Depends(get_db), user_id: int = Depends(current_user_id)) -> list[dict]:
    return await CreatorPlatformService(db, get_settings()).list_content(user_id, status=status_filter)


@router.get("/{content_id}", response_model=ContentResponse)
async def get_content(content_id: int, db: AsyncSession = Depends(get_db), user_id: int = Depends(current_user_id)) -> dict:
    service = CreatorPlatformService(db, get_settings())
    item = await service.get_content(user_id, content_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Content not found")
    return await service._content_response(item)


@router.patch("/{content_id}", response_model=ContentResponse)
async def update_content(content_id: int, values: ContentUpdate, db: AsyncSession = Depends(get_db), user_id: int = Depends(current_user_id)) -> dict:
    try:
        item = await CreatorPlatformService(db, get_settings()).update_content(user_id, content_id, values)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if item is None:
        raise HTTPException(status_code=404, detail="Content not found")
    return item


@router.post("/{content_id}/publish", response_model=ContentResponse)
async def publish_content(content_id: int, db: AsyncSession = Depends(get_db), user_id: int = Depends(current_user_id)) -> dict:
    try:
        return await CreatorPlatformService(db, get_settings()).publish_content(user_id, content_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, SocialIntegrationError) as exc:
        raise HTTPException(status_code=502 if isinstance(exc, SocialIntegrationError) else 400, detail=str(exc)) from exc

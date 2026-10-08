from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.api.v1.social_accounts import current_user_id
from app.schemas.creator_platform import ContentCreate, ContentResponse, ContentUpdate
from app.services.creator_platform_service import CreatorPlatformService

router = APIRouter(prefix="/content", tags=["content management"])


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


@router.post("/{content_id}/publish", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def publish_content(content_id: int, db: AsyncSession = Depends(get_db), user_id: int = Depends(current_user_id)) -> None:
    item = await CreatorPlatformService(db, get_settings()).get_content(user_id, content_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Content not found")
    raise HTTPException(status_code=501, detail="Publishing requires Facebook and YouTube write permissions and provider upload integrations")
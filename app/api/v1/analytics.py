from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.integrations.youtube import YouTubeIntegration
from app.models.social_account import Platform
from app.api.v1.social_accounts import current_user_id
from app.schemas.creator_platform import MetricSnapshotCreate, MetricSnapshotResponse
from app.services.creator_platform_service import CreatorPlatformService
from app.services.social_account_service import SocialAccountService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview")
async def analytics_overview(db: AsyncSession = Depends(get_db), user_id: int = Depends(current_user_id)) -> dict:
    return await CreatorPlatformService(db, get_settings()).overview_analytics(user_id)


@router.get("/creators/{creator_user_id}")
async def public_creator_analytics(creator_user_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    analytics = await CreatorPlatformService(db, get_settings()).public_creator_analytics(creator_user_id)
    if analytics is None:
        raise HTTPException(status_code=404, detail="Public creator profile not found")
    return analytics


@router.get("/accounts/{account_id}")
async def account_analytics(account_id: int, db: AsyncSession = Depends(get_db), user_id: int = Depends(current_user_id)) -> dict:
    analytics = await CreatorPlatformService(db, get_settings()).account_analytics(user_id, account_id)
    if analytics is None:
        raise HTTPException(status_code=404, detail="Social account not found")
    return analytics


@router.get("/accounts/{account_id}/youtube")
async def youtube_analytics(
    account_id: int,
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(current_user_id),
) -> dict:
    settings = get_settings()
    account = await SocialAccountService(db, settings).get_account(user_id, account_id)
    if account is None or account.platform != Platform.YOUTUBE:
        raise HTTPException(status_code=404, detail="YouTube account not found")
    end = end_date or date.today()
    start = start_date or end - timedelta(days=28)
    if start > end:
        raise HTTPException(status_code=422, detail="start_date must be before or equal to end_date")
    token = await SocialAccountService(db, settings).valid_token(account)
    return await YouTubeIntegration(settings).get_analytics(token, start, end)


@router.post("/accounts/{account_id}/snapshots", response_model=MetricSnapshotResponse, status_code=status.HTTP_201_CREATED)
async def record_metric_snapshot(account_id: int, values: MetricSnapshotCreate, db: AsyncSession = Depends(get_db), user_id: int = Depends(current_user_id)) -> MetricSnapshotResponse:
    snapshot = await CreatorPlatformService(db, get_settings()).add_metric_snapshot(user_id, account_id, values)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Social account not found")
    return snapshot


@router.get("/accounts/{account_id}/snapshots", response_model=list[MetricSnapshotResponse])
async def account_metric_snapshots(account_id: int, db: AsyncSession = Depends(get_db), user_id: int = Depends(current_user_id)) -> list[MetricSnapshotResponse]:
    snapshots = await CreatorPlatformService(db, get_settings()).list_metric_snapshots(user_id, account_id)
    if snapshots is None:
        raise HTTPException(status_code=404, detail="Social account not found")
    return snapshots
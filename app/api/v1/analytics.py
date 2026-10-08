from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.api.v1.social_accounts import current_user_id
from app.schemas.creator_platform import MetricSnapshotCreate, MetricSnapshotResponse
from app.services.creator_platform_service import CreatorPlatformService

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
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.security import current_user_id, validate_oauth_state
from app.integrations.base import SocialIntegrationError
from app.models.social_account import Platform
from app.schemas.social_account import InfluencerUpdate, SocialAccountResponse, SyncResponse
from app.schemas.video import VideoListResponse
from app.services.social_account_service import SocialAccountService
from app.services.platform_service import PlatformService, PlatformTemporarilyDisabledError
from app.services.video_service import VideoService

router = APIRouter(prefix="/social", tags=["social accounts"])


def require_enabled_platform(platform: Platform, settings: Settings) -> None:
    try:
        PlatformService(settings).require_enabled(platform)
    except PlatformTemporarilyDisabledError as exc:
        raise HTTPException(status_code=404, detail="Platform temporarily disabled") from exc


@router.get("/{platform}/connect")
async def connect_platform(platform: Platform, user_id: int = Depends(current_user_id), settings: Settings = Depends(get_settings)) -> dict[str, str]:
    require_enabled_platform(platform, settings)
    return {"authorization_url": SocialAccountService(None, settings).authorization_url(user_id, platform)}


@router.get("/{platform}/callback", response_model=SocialAccountResponse)
async def oauth_callback(platform: Platform, code: str | None = Query(default=None), state: str | None = Query(default=None), error: str | None = Query(default=None), error_description: str | None = Query(default=None), db: AsyncSession = Depends(get_db), settings: Settings = Depends(get_settings)) -> SocialAccountResponse:
    require_enabled_platform(platform, settings)
    if error:
        detail = error_description or error
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{platform.value} authorization was not completed: {detail}")
    if not code or not state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth callback requires code and state")
    user_id = validate_oauth_state(state, platform.value)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state")
    try:
        return await SocialAccountService(db, settings).connect(user_id, platform, code)
    except SocialIntegrationError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"{platform.value} connection failed: {exc}") from exc


@router.get("/accounts", response_model=list[SocialAccountResponse])
async def accounts(db: AsyncSession = Depends(get_db), user_id: int = Depends(current_user_id)) -> list[SocialAccountResponse]:
    return await SocialAccountService(db, get_settings()).list_accounts(user_id)


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_account(account_id: int, db: AsyncSession = Depends(get_db), user_id: int = Depends(current_user_id)) -> None:
    disconnected = await SocialAccountService(db, get_settings()).disconnect(user_id, account_id)
    if not disconnected:
        raise HTTPException(status_code=404, detail="Social account not found")


@router.patch("/accounts/{account_id}/influencer", response_model=SocialAccountResponse)
async def update_account_influencer(account_id: int, update: InfluencerUpdate, db: AsyncSession = Depends(get_db), user_id: int = Depends(current_user_id)) -> SocialAccountResponse:
    account = await SocialAccountService(db, get_settings()).set_influencer(user_id, account_id, update.is_influencer)
    if account is None:
        raise HTTPException(status_code=404, detail="Social account not found")
    return account


@router.get("/accounts/{account_id}/videos", response_model=VideoListResponse)
async def account_videos(account_id: int, db: AsyncSession = Depends(get_db), user_id: int = Depends(current_user_id)) -> dict:
    account = await SocialAccountService(db, get_settings()).get_account(user_id, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Social account not found")
    videos = await VideoService(db, get_settings()).list_videos(account)
    return {"platform": account.platform.value, "videos": videos, "count": len(videos)}


@router.post("/accounts/{account_id}/sync", response_model=SyncResponse)
async def sync_account(account_id: int, db: AsyncSession = Depends(get_db), user_id: int = Depends(current_user_id)) -> SyncResponse:
    settings = get_settings()
    account = await SocialAccountService(db, settings).get_account(user_id, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Social account not found")
    try:
        videos = await VideoService(db, settings).sync(account)
    except SocialIntegrationError as exc:
        raise HTTPException(status_code=502, detail="Platform sync failed") from exc
    return {"account_id": account.id, "platform": account.platform, "count": len(videos), "videos": videos}

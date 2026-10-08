from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.api.v1.social_accounts import current_user_id
from app.schemas.creator_platform import BrandProfileCreate, BrandProfileResponse, BrandProfileUpdate, CampaignCreate, CampaignResponse, CampaignUpdate, CollaborationCreate, CollaborationDecision, CollaborationProgress, CollaborationResponse, CreatorProfileCreate, CreatorProfileResponse, CreatorProfileUpdate
from app.services.creator_platform_service import CreatorPlatformService

router = APIRouter(tags=["creator and brand marketplace"])


@router.post("/creators/me", response_model=CreatorProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_creator_profile(values: CreatorProfileCreate, db: AsyncSession = Depends(get_db), user_id: int = Depends(current_user_id)) -> CreatorProfileResponse:
    service = CreatorPlatformService(db, get_settings())
    profile = await service.save_creator_profile(user_id, values)
    return await service.creator_profile_data(profile)


@router.get("/creators/me", response_model=CreatorProfileResponse)
async def get_creator_profile(db: AsyncSession = Depends(get_db), user_id: int = Depends(current_user_id)) -> CreatorProfileResponse:
    service = CreatorPlatformService(db, get_settings())
    profile = await service.creator_profile(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Creator profile not found")
    return await service.creator_profile_data(profile)


@router.patch("/creators/me", response_model=CreatorProfileResponse)
async def update_creator_profile(values: CreatorProfileUpdate, db: AsyncSession = Depends(get_db), user_id: int = Depends(current_user_id)) -> CreatorProfileResponse:
    service = CreatorPlatformService(db, get_settings())
    if await service.creator_profile(user_id) is None:
        raise HTTPException(status_code=404, detail="Creator profile not found")
    profile = await service.save_creator_profile(user_id, values)
    return await service.creator_profile_data(profile)


@router.get("/creators/discover", response_model=list[CreatorProfileResponse])
async def discover_creators(niche: str | None = Query(default=None, max_length=120), db: AsyncSession = Depends(get_db)) -> list[CreatorProfileResponse]:
    return await CreatorPlatformService(db, get_settings()).discover_creators(niche)


@router.get("/creators/{creator_user_id}", response_model=CreatorProfileResponse)
async def public_creator_profile(creator_user_id: int, db: AsyncSession = Depends(get_db)) -> CreatorProfileResponse:
    profile = await CreatorPlatformService(db, get_settings()).public_creator_profile(creator_user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Public creator profile not found")
    return profile


@router.post("/brands/me", response_model=BrandProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_brand_profile(values: BrandProfileCreate, db: AsyncSession = Depends(get_db), user_id: int = Depends(current_user_id)) -> BrandProfileResponse:
    return await CreatorPlatformService(db, get_settings()).save_brand_profile(user_id, values)


@router.get("/brands/me", response_model=BrandProfileResponse)
async def get_brand_profile(db: AsyncSession = Depends(get_db), user_id: int = Depends(current_user_id)) -> BrandProfileResponse:
    profile = await CreatorPlatformService(db, get_settings()).brand_profile(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Brand profile not found")
    return profile


@router.patch("/brands/me", response_model=BrandProfileResponse)
async def update_brand_profile(values: BrandProfileUpdate, db: AsyncSession = Depends(get_db), user_id: int = Depends(current_user_id)) -> BrandProfileResponse:
    service = CreatorPlatformService(db, get_settings())
    if await service.brand_profile(user_id) is None:
        raise HTTPException(status_code=404, detail="Brand profile not found")
    return await service.save_brand_profile(user_id, values)


@router.post("/brands/me/campaigns", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(values: CampaignCreate, db: AsyncSession = Depends(get_db), user_id: int = Depends(current_user_id)) -> CampaignResponse:
    try:
        campaign = await CreatorPlatformService(db, get_settings()).save_campaign(user_id, values)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return campaign


@router.get("/brands/me/campaigns", response_model=list[CampaignResponse])
async def brand_campaigns(db: AsyncSession = Depends(get_db), user_id: int = Depends(current_user_id)) -> list[CampaignResponse]:
    return await CreatorPlatformService(db, get_settings()).list_campaigns(user_id=user_id)


@router.patch("/brands/me/campaigns/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(campaign_id: int, values: CampaignUpdate, db: AsyncSession = Depends(get_db), user_id: int = Depends(current_user_id)) -> CampaignResponse:
    try:
        campaign = await CreatorPlatformService(db, get_settings()).save_campaign(user_id, values, campaign_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.get("/campaigns", response_model=list[CampaignResponse])
async def discover_campaigns(db: AsyncSession = Depends(get_db)) -> list[CampaignResponse]:
    return await CreatorPlatformService(db, get_settings()).list_campaigns(open_only=True)


@router.post("/brands/me/collaborations", response_model=CollaborationResponse, status_code=status.HTTP_201_CREATED)
async def invite_creator(values: CollaborationCreate, db: AsyncSession = Depends(get_db), user_id: int = Depends(current_user_id)) -> CollaborationResponse:
    try:
        return await CreatorPlatformService(db, get_settings()).create_collaboration(user_id, values)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/brands/me/collaborations", response_model=list[CollaborationResponse])
async def sent_collaborations(db: AsyncSession = Depends(get_db), user_id: int = Depends(current_user_id)) -> list[CollaborationResponse]:
    return await CreatorPlatformService(db, get_settings()).list_collaborations(user_id, as_creator=False)


@router.patch("/brands/me/collaborations/{request_id}", response_model=CollaborationResponse)
async def update_collaboration_progress(request_id: int, values: CollaborationProgress, db: AsyncSession = Depends(get_db), user_id: int = Depends(current_user_id)) -> CollaborationResponse:
    try:
        request = await CreatorPlatformService(db, get_settings()).update_collaboration(user_id, request_id, values.status, as_creator=False)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if request is None:
        raise HTTPException(status_code=404, detail="Collaboration request not found")
    return request


@router.get("/creators/me/collaborations", response_model=list[CollaborationResponse])
async def received_collaborations(db: AsyncSession = Depends(get_db), user_id: int = Depends(current_user_id)) -> list[CollaborationResponse]:
    return await CreatorPlatformService(db, get_settings()).list_collaborations(user_id, as_creator=True)


@router.patch("/creators/me/collaborations/{request_id}", response_model=CollaborationResponse)
async def respond_to_collaboration(request_id: int, values: CollaborationDecision, db: AsyncSession = Depends(get_db), user_id: int = Depends(current_user_id)) -> CollaborationResponse:
    try:
        request = await CreatorPlatformService(db, get_settings()).update_collaboration(user_id, request_id, values.status, as_creator=True)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if request is None:
        raise HTTPException(status_code=404, detail="Collaboration request not found")
    return request
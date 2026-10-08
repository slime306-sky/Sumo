from fastapi import APIRouter

from app.api.v1.analytics import router as analytics_router
from app.api.v1.content import router as content_router
from app.api.v1.creator_marketplace import router as marketplace_router
from app.api.v1.social_accounts import router as social_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(social_router)
api_router.include_router(content_router)
api_router.include_router(marketplace_router)
api_router.include_router(analytics_router)

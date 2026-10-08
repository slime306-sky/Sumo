from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.logging import configure_logging
from app.integrations.base import RateLimitError, SocialIntegrationError
from app.services.platform_service import PlatformTemporarilyDisabledError


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    yield


app = FastAPI(title="Sumo Social API", version="0.1.0", lifespan=lifespan)
app.include_router(api_router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(RateLimitError)
async def rate_limit_handler(_, __) -> JSONResponse:
    return JSONResponse(status_code=429, content={"detail": "Platform rate limit reached"})


@app.exception_handler(SocialIntegrationError)
async def integration_error_handler(_, exc: SocialIntegrationError) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.exception_handler(PlatformTemporarilyDisabledError)
async def disabled_platform_handler(_, __) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": "Platform temporarily disabled"})

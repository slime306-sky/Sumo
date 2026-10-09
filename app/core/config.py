from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Sumo Social API"
    app_env: str = "development"
    secret_key: str = Field(default="change-me", min_length=1)
    access_token_expire_minutes: int = Field(default=60, ge=1)
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/sumo"
    oauth_success_redirect: str = "http://localhost:3000/settings/social"
    request_timeout_seconds: float = 20.0
    enabled_social_platforms: str = "youtube,facebook"
    cors_origins: str = "http://localhost:3000"
    facebook_app_id: str | None = None
    facebook_app_secret: str | None = None
    facebook_config_id: str | None = None
    facebook_redirect_uri: str | None = None
    facebook_graph_api_version: str = "v23.0"
    youtube_client_id: str | None = None
    youtube_client_secret: str | None = None
    youtube_redirect_uri: str | None = None
    cloudinary_cloud_name: str | None = None
    cloudinary_api_key: str | None = None
    cloudinary_api_secret: str | None = None
    cloudinary_upload_folder: str = "sumo/videos"
    max_video_upload_bytes: int = Field(default=524288000, ge=1)
    max_profile_image_upload_bytes: int = Field(default=10485760, ge=1)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def enabled_platform_names(self) -> frozenset[str]:
        return frozenset(name.strip().lower() for name in self.enabled_social_platforms.split(",") if name.strip())

    @property
    def cors_origin_names(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

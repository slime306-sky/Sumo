from app.core.config import Settings
from app.models.social_account import Platform


class PlatformTemporarilyDisabledError(Exception):
    pass


class PlatformService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def is_enabled(self, platform: Platform) -> bool:
        return platform.value in self.settings.enabled_platform_names

    def require_enabled(self, platform: Platform) -> None:
        if not self.is_enabled(platform):
            raise PlatformTemporarilyDisabledError(platform.value)
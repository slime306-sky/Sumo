from app.core.config import Settings
from app.integrations.base import SocialPlatform, UnsupportedPlatformError
from app.integrations.facebook import FacebookIntegration
from app.integrations.youtube import YouTubeIntegration
from app.models.social_account import Platform


INTEGRATIONS = {
    Platform.FACEBOOK: FacebookIntegration,
    Platform.YOUTUBE: YouTubeIntegration,
}


def get_integration(platform: Platform, settings: Settings) -> SocialPlatform:
    integration = INTEGRATIONS.get(platform)
    if integration is None:
        raise UnsupportedPlatformError(f"Unsupported platform: {platform}")
    return integration(settings)

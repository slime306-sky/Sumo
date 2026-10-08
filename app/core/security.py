import hashlib
import hmac
import secrets

from app.core.config import get_settings


def create_oauth_state(user_id: int, platform: str) -> str:
    payload = f"{user_id}:{platform}:{secrets.token_urlsafe(24)}"
    signature = hmac.new(get_settings().secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{signature}"


def validate_oauth_state(state: str, platform: str, expected_user_id: int | None = None) -> int | None:
    parts = state.split(":", 3)
    if len(parts) != 4 or parts[1] != platform:
        return None
    try:
        user_id = int(parts[0])
    except ValueError:
        return None
    if expected_user_id is not None and user_id != expected_user_id:
        return None
    payload, signature = state.rsplit(":", 1)
    expected = hmac.new(get_settings().secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return user_id if hmac.compare_digest(signature, expected) else None

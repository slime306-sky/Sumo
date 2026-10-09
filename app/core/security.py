import base64
import binascii
import hashlib
import hmac
import json
import secrets
import time

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings

_PASSWORD_ITERATIONS = 600_000
_bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${_PASSWORD_ITERATIONS}${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_value, digest_value = encoded.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_value.encode())
        expected = base64.urlsafe_b64decode(digest_value.encode())
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iterations))
    except (ValueError, TypeError, binascii.Error):
        return False
    return hmac.compare_digest(actual, expected)


def _encode_segment(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _decode_segment(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def create_access_token(user_id: int, role: str) -> str:
    payload = {"sub": str(user_id), "role": role, "exp": int(time.time()) + get_settings().access_token_expire_minutes * 60}
    encoded_payload = _encode_segment(json.dumps(payload, separators=(",", ":")).encode())
    signature = hmac.new(get_settings().secret_key.encode(), encoded_payload.encode(), hashlib.sha256).digest()
    return f"{encoded_payload}.{_encode_segment(signature)}"


def decode_access_token(token: str) -> dict[str, str]:
    try:
        encoded_payload, encoded_signature = token.split(".")
        expected = hmac.new(get_settings().secret_key.encode(), encoded_payload.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(_decode_segment(encoded_signature), expected):
            raise ValueError
        payload = json.loads(_decode_segment(encoded_payload))
        user_id = int(payload["sub"])
        role = payload["role"]
        if role not in {"creator", "company"} or int(payload["exp"]) <= int(time.time()):
            raise ValueError
    except (ValueError, TypeError, KeyError, UnicodeDecodeError, binascii.Error, json.JSONDecodeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired bearer token", headers={"WWW-Authenticate": "Bearer"})
    return {"user_id": str(user_id), "role": role}


def current_user_id(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme)) -> int:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required", headers={"WWW-Authenticate": "Bearer"})
    return int(decode_access_token(credentials.credentials)["user_id"])


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

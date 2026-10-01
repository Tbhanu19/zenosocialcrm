"""Password hashing and JWT helpers.

Passwords and tokens must never be logged by callers of this module.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import get_settings

_password_hash = PasswordHash.recommended()
# Verified when the email does not match a user so the response time stays similar.
_DUMMY_PASSWORD_HASH = _password_hash.hash("dummy-password-not-used-for-login")


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bool(_password_hash.verify(password, password_hash))
    except (ValueError, TypeError):
        return False


def verify_password_for_missing_user(password: str) -> None:
    verify_password(password, _DUMMY_PASSWORD_HASH)


@dataclass(frozen=True)
class AccessTokenClaims:
    user_id: UUID
    token_version: int


def create_access_token(user_id: UUID, token_version: int) -> str:
    settings = get_settings()
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": str(user_id), "ver": token_version, "exp": expires_at}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> AccessTokenClaims:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except InvalidTokenError as exc:
        raise ValueError("Invalid token") from exc
    subject = payload.get("sub")
    version = payload.get("ver")
    if not isinstance(subject, str) or isinstance(version, bool) or not isinstance(version, int):
        raise ValueError("Invalid token")
    try:
        user_id = UUID(subject)
    except ValueError as exc:
        raise ValueError("Invalid token") from exc
    return AccessTokenClaims(user_id=user_id, token_version=version)

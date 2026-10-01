"""User creation and credential checks."""

import logging
from typing import NoReturn

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.permissions import UserStatus
from app.core.security import hash_password, verify_password, verify_password_for_missing_user
from app.models.user import User
from app.schemas.user import ProfileUpdate, UserCreate

logger = logging.getLogger("zenosocialcrm.auth")
INVALID_CREDENTIALS = "Invalid email or password."


def create_user(db: Session, data: UserCreate) -> User:
    email = data.normalized_email()
    existing = db.scalar(select(User.id).where(User.email == email))
    if existing is not None:
        raise ConflictError("A user with this email already exists.")

    user = User(
        email=email,
        password_hash=hash_password(data.password),
        first_name=data.first_name.strip(),
        last_name=data.last_name.strip(),
        status=data.status.value,
        is_super_admin=data.is_super_admin,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("A user with this email already exists.") from None
    db.refresh(user)
    return user


def update_profile(db: Session, user: User, data: ProfileUpdate) -> User:
    email = data.normalized_email()
    if email != user.email:
        existing = db.scalar(select(User.id).where(User.email == email))
        if existing is not None:
            raise ConflictError("A user with this email already exists.")
        user.email = email
    user.first_name = data.first_name
    user.last_name = data.last_name
    user.phone = data.phone
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("A user with this email already exists.") from None
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    normalized = email.strip().lower()
    user = db.scalar(select(User).where(User.email == normalized))
    if user is None:
        verify_password_for_missing_user(password)
        _reject("unknown_email")
    if not verify_password(password, user.password_hash):
        _reject("bad_password")
    if user.status != UserStatus.ACTIVE.value:
        # Invited accounts are not authenticated until an invitation flow exists.
        reason = "invited" if user.status == UserStatus.INVITED.value else "inactive"
        _reject(reason)
    return user


def revoke_access_tokens(db: Session, user: User) -> None:
    """Invalidate every access token already issued for this user."""
    user.token_version += 1
    db.commit()


def _reject(reason: str) -> NoReturn:
    logger.info("authentication failed reason=%s", reason)
    raise UnauthorizedError(INVALID_CREDENTIALS)

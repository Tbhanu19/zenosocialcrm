"""FastAPI dependencies for the current user and company access."""

from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ForbiddenError, UnauthorizedError
from app.core.permissions import CRM_WRITER_ROLES, USER_MANAGER_ROLES, UserRole, UserStatus
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.services.authorization_service import CompanyAccess, authorize_company_access

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError()
    try:
        claims = decode_access_token(credentials.credentials)
    except ValueError:
        raise UnauthorizedError("Invalid or expired token.") from None
    user = db.get(User, claims.user_id)
    if (
        user is None
        or user.status != UserStatus.ACTIVE.value
        or user.token_version != claims.token_version
    ):
        raise UnauthorizedError("Invalid or expired token.")
    return user


def require_super_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_super_admin:
        raise ForbiddenError("Super admin access is required.")
    return current_user


def require_user_manager(
    company_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyAccess:
    """Company access plus permission to manage that company's users."""
    access = authorize_company_access(db, current_user, company_id)
    if access.role not in USER_MANAGER_ROLES:
        raise ForbiddenError()
    return access


def require_crm_writer(
    company_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyAccess:
    """Company access plus permission to create or change CRM records."""
    access = authorize_company_access(db, current_user, company_id)
    if access.role not in CRM_WRITER_ROLES:
        raise ForbiddenError("Your role does not allow this action.")
    return access


def require_company_access(
    company_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyAccess:
    return authorize_company_access(db, current_user, company_id)


def get_current_company(
    x_company_id: Annotated[UUID | None, Header()] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyAccess:
    """Resolve the company context header. The id is authorized before use."""
    if x_company_id is None:
        raise BadRequestError("X-Company-Id header is required.")
    return authorize_company_access(db, current_user, x_company_id)


require_authenticated_user = get_current_user


def require_company_role(*roles: UserRole) -> Callable[..., CompanyAccess]:
    """Require a company membership whose role is one of the given roles."""
    return require_role(*roles)


def require_role(*roles: UserRole) -> Callable[..., CompanyAccess]:
    allowed = frozenset(roles)

    def dependency(
        company_id: UUID,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> CompanyAccess:
        return authorize_company_access(
            db,
            current_user,
            company_id,
            required_roles=allowed,
        )

    return dependency

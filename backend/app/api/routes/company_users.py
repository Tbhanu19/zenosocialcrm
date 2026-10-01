"""Company-scoped user management."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_user_manager
from app.core.permissions import UserRole
from app.db.session import get_db
from app.models.user import User
from app.schemas.pagination import Page
from app.schemas.user import (
    CompanyMemberCreate,
    CompanyMemberRead,
    CompanyMemberUpdate,
    MemberListStatus,
)
from app.services.authorization_service import CompanyAccess
from app.services.user_admin_service import (
    add_company_user,
    list_company_users,
    update_company_user,
)

router = APIRouter(prefix="/companies/{company_id}/users", tags=["company-users"])


@router.get("", response_model=Page[CompanyMemberRead])
def company_user_list(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=100),
    role: UserRole | None = None,
    status: MemberListStatus | None = None,
    db: Session = Depends(get_db),
    access: CompanyAccess = Depends(require_user_manager),
) -> Page[CompanyMemberRead]:
    return list_company_users(
        db,
        access.company.id,
        page=page,
        page_size=page_size,
        search=search,
        role=role,
        status=status,
    )


@router.post("", response_model=CompanyMemberRead, status_code=201)
def company_user_create(
    body: CompanyMemberCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
    access: CompanyAccess = Depends(require_user_manager),
) -> CompanyMemberRead:
    return add_company_user(db, actor, access, body)


@router.patch("/{user_id}", response_model=CompanyMemberRead)
def company_user_update(
    user_id: UUID,
    body: CompanyMemberUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
    access: CompanyAccess = Depends(require_user_manager),
) -> CompanyMemberRead:
    return update_company_user(db, actor, access, user_id, body)

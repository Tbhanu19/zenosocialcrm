"""Platform-wide user directory for super admins."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_super_admin
from app.core.permissions import UserRole
from app.db.session import get_db
from app.models.user import User
from app.schemas.pagination import Page
from app.schemas.user import AdminUserRow, MemberListStatus
from app.services.user_admin_service import list_all_users

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


@router.get("", response_model=Page[AdminUserRow])
def admin_user_list(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=100),
    role: UserRole | None = None,
    status: MemberListStatus | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
) -> Page[AdminUserRow]:
    return list_all_users(
        db,
        page=page,
        page_size=page_size,
        search=search,
        role=role,
        status=status,
    )

"""Company-scoped user management.

Membership status is changed for the requested company only. A person who
belongs to another company keeps that other membership.
"""

import logging
import secrets
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.core.exceptions import (
    AppError,
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from app.core.permissions import (
    COMPANY_MEMBERSHIP_ROLES,
    MembershipStatus,
    UserRole,
    UserStatus,
    roles_assignable_by,
)
from app.core.search import contains_pattern
from app.core.security import hash_password
from app.models.company import Company
from app.models.user import User
from app.models.user_company import UserCompany
from app.schemas.pagination import Page, total_pages
from app.schemas.user import (
    AdminUserRow,
    CompanyMemberCreate,
    CompanyMemberRead,
    CompanyMemberUpdate,
    MemberListStatus,
)
from app.services.authorization_service import CompanyAccess

logger = logging.getLogger("zenosocialcrm.users")


def list_company_users(
    db: Session,
    company_id: UUID,
    *,
    page: int,
    page_size: int,
    search: str | None,
    role: UserRole | None,
    status: MemberListStatus | None,
) -> Page[CompanyMemberRead]:
    filters = _member_filters(company_id=company_id, search=search, role=role, status=status)
    total = _count_members(db, filters)
    rows = db.execute(
        select(User, UserCompany)
        .join(UserCompany, UserCompany.user_id == User.id)
        .where(*filters)
        .order_by(User.last_name, User.first_name, User.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page(
        items=[_member_read(user, membership) for user, membership in rows],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages(total, page_size),
    )


def list_all_users(
    db: Session,
    *,
    page: int,
    page_size: int,
    search: str | None,
    role: UserRole | None,
    status: MemberListStatus | None,
) -> Page[AdminUserRow]:
    filters = _member_filters(company_id=None, search=search, role=role, status=status)
    total = _count_members(db, filters, include_company=True)
    rows = db.execute(
        select(User, UserCompany, Company)
        .join(UserCompany, UserCompany.user_id == User.id)
        .join(Company, Company.id == UserCompany.company_id)
        .where(*filters)
        .order_by(User.last_name, User.first_name, Company.name, UserCompany.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items = [
        AdminUserRow(
            **_member_read(user, membership).model_dump(),
            company_id=company.id,
            company_name=company.name,
        )
        for user, membership, company in rows
    ]
    return Page(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages(total, page_size),
    )


def add_company_user(
    db: Session,
    actor: User,
    access: CompanyAccess,
    data: CompanyMemberCreate,
) -> CompanyMemberRead:
    _require_assignable(access.role, data.role)
    email = data.normalized_email()
    try:
        existing = db.scalar(select(User).where(User.email == email))
        if existing is None:
            user = User(
                email=email,
                password_hash=hash_password(secrets.token_urlsafe(32)),
                first_name=data.first_name.strip(),
                last_name=data.last_name.strip(),
                phone=data.phone,
                status=UserStatus.INVITED.value,
                is_super_admin=False,
            )
            db.add(user)
            db.flush()
        else:
            if existing.is_super_admin:
                raise ConflictError("This account cannot be added to a company.")
            user = existing
        already = db.scalar(
            select(UserCompany.id).where(
                UserCompany.user_id == user.id,
                UserCompany.company_id == access.company.id,
            )
        )
        if already is not None:
            raise ConflictError("This user already belongs to this company.")
        membership = UserCompany(
            user_id=user.id,
            company_id=access.company.id,
            role=data.role.value,
            status=data.membership_status.value,
        )
        db.add(membership)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("This user already belongs to this company.") from None
    except AppError:
        db.rollback()
        raise
    db.refresh(user)
    db.refresh(membership)
    logger.info(
        "company user added actor_id=%s company_id=%s user_id=%s",
        actor.id,
        access.company.id,
        user.id,
    )
    return _member_read(user, membership)


def update_company_user(
    db: Session,
    actor: User,
    access: CompanyAccess,
    user_id: UUID,
    data: CompanyMemberUpdate,
) -> CompanyMemberRead:
    if not data.model_fields_set:
        raise BadRequestError("At least one field is required.")
    row = db.execute(
        select(User, UserCompany)
        .join(UserCompany, UserCompany.user_id == User.id)
        .where(
            UserCompany.company_id == access.company.id,
            UserCompany.user_id == user_id,
        )
    ).one_or_none()
    if row is None:
        raise NotFoundError("User not found.")
    user, membership = row
    current_role = UserRole(membership.role)
    if current_role not in roles_assignable_by(access.role):
        raise ForbiddenError("You cannot change this user.")
    if user.id == actor.id and {"role", "membership_status"} & data.model_fields_set:
        raise ForbiddenError("You cannot change your own access.")
    if "role" in data.model_fields_set and data.role is not None:
        _require_assignable(access.role, data.role)
        membership.role = data.role.value
    if "membership_status" in data.model_fields_set and data.membership_status is not None:
        membership.status = data.membership_status.value
    if "first_name" in data.model_fields_set and data.first_name is not None:
        user.first_name = data.first_name
    if "last_name" in data.model_fields_set and data.last_name is not None:
        user.last_name = data.last_name
    if "phone" in data.model_fields_set:
        user.phone = data.phone
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise BadRequestError("The user could not be saved.") from None
    db.refresh(user)
    db.refresh(membership)
    logger.info(
        "company user updated actor_id=%s company_id=%s user_id=%s",
        actor.id,
        access.company.id,
        user.id,
    )
    return _member_read(user, membership)


def _require_assignable(actor_role: UserRole, requested: UserRole) -> None:
    allowed = requested in roles_assignable_by(actor_role)
    if not allowed or requested not in COMPANY_MEMBERSHIP_ROLES:
        raise ForbiddenError("You cannot assign that role.")


def _member_filters(
    *,
    company_id: UUID | None,
    search: str | None,
    role: UserRole | None,
    status: MemberListStatus | None,
) -> list[ColumnElement[bool]]:
    filters: list[ColumnElement[bool]] = []
    if company_id is not None:
        filters.append(UserCompany.company_id == company_id)
    if role is not None:
        if role not in COMPANY_MEMBERSHIP_ROLES:
            raise BadRequestError("That role is not a company role.")
        filters.append(UserCompany.role == role.value)
    if status is MemberListStatus.INVITED:
        filters.append(User.status == UserStatus.INVITED.value)
    elif status is not None:
        filters.append(UserCompany.status == status.value)
    if search is not None and search.strip():
        pattern = contains_pattern(search.strip())
        filters.append(
            or_(
                User.first_name.ilike(pattern, escape="\\"),
                User.last_name.ilike(pattern, escape="\\"),
                User.email.ilike(pattern, escape="\\"),
                User.phone.ilike(pattern, escape="\\"),
            )
        )
    return filters


def _count_members(
    db: Session,
    filters: list[ColumnElement[bool]],
    *,
    include_company: bool = False,
) -> int:
    stmt = (
        select(func.count())
        .select_from(UserCompany)
        .join(User, User.id == UserCompany.user_id)
    )
    if include_company:
        stmt = stmt.join(Company, Company.id == UserCompany.company_id)
    if filters:
        stmt = stmt.where(*filters)
    return db.scalar(stmt) or 0


def _member_read(user: User, membership: UserCompany) -> CompanyMemberRead:
    return CompanyMemberRead(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        phone=user.phone,
        role=UserRole(membership.role),
        membership_status=MembershipStatus(membership.status),
        user_status=UserStatus(user.status),
        created_at=membership.created_at,
    )

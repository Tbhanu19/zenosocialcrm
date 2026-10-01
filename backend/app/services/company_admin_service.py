"""Super-admin company administration.

Company creation and the initial owner membership commit together.
"""

import logging
import secrets
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.core.exceptions import AppError, BadRequestError, ConflictError
from app.core.permissions import CompanyStatus, MembershipStatus, UserRole, UserStatus
from app.core.search import contains_pattern
from app.core.security import hash_password
from app.models.campaign import MarketingCampaign
from app.models.company import Company
from app.models.contact import Contact
from app.models.lead import Lead
from app.models.message import Message
from app.models.pipeline import SalesPipeline
from app.models.user import User
from app.models.user_company import UserCompany
from app.schemas.company import (
    AdminCompanyCreate,
    AdminCompanyCreated,
    AdminCompanyDetail,
    AdminCompanyListItem,
    CompanyRead,
    CompanyUpdate,
    OwnerSeed,
    ProvisionedOwner,
    RoleCounts,
)
from app.schemas.pagination import Page, total_pages

logger = logging.getLogger("zenosocialcrm.companies")


def list_companies(
    db: Session,
    *,
    page: int,
    page_size: int,
    search: str | None,
    status: CompanyStatus | None,
    business_type: str | None,
) -> Page[AdminCompanyListItem]:
    filters = _company_filters(search, status, business_type)
    count_stmt = select(func.count()).select_from(Company)
    list_stmt = select(Company).order_by(Company.name, Company.id)
    if filters:
        count_stmt = count_stmt.where(*filters)
        list_stmt = list_stmt.where(*filters)
    total = db.scalar(count_stmt) or 0
    companies = db.scalars(list_stmt.offset((page - 1) * page_size).limit(page_size)).all()
    owners = _primary_owners(db, [company.id for company in companies])
    items: list[AdminCompanyListItem] = []
    for company in companies:
        owner = owners.get(company.id)
        items.append(
            AdminCompanyListItem(
                id=company.id,
                name=company.name,
                business_type=company.business_type,
                status=CompanyStatus(company.status),
                created_at=company.created_at,
                owner_name=None if owner is None else owner[0],
                owner_email=None if owner is None else owner[1],
            )
        )
    return Page(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages(total, page_size),
    )


def get_company_detail(db: Session, company: Company) -> AdminCompanyDetail:
    counts = RoleCounts()
    rows = db.execute(
        select(UserCompany.role, func.count())
        .where(UserCompany.company_id == company.id)
        .group_by(UserCompany.role)
    ).all()
    for role, count in rows:
        amount = int(count)
        if role == UserRole.OWNER.value:
            counts.owners = amount
        elif role == UserRole.COMPANY_MANAGER.value:
            counts.company_managers = amount
        elif role == UserRole.MARKETING_MANAGER.value:
            counts.marketing_managers = amount
        elif role == UserRole.EMPLOYEE.value:
            counts.employees = amount
    detail = AdminCompanyDetail.model_validate(company)
    return detail.model_copy(update={"counts": counts})


def create_company_with_owner(
    db: Session,
    actor: User,
    data: AdminCompanyCreate,
) -> AdminCompanyCreated:
    company = Company(
        name=data.name.strip(),
        business_type=data.business_type,
        phone=data.phone,
        email=data.email,
        website=data.website,
        address=data.address,
        city=data.city,
        state=data.state,
        zip_code=data.zip_code,
        status=data.status.value,
    )
    db.add(company)
    try:
        db.flush()
        owner, linked_existing = _resolve_owner(db, data.owner)
        if owner.is_super_admin:
            raise ConflictError("This account cannot be assigned as a company owner.")
        db.add(
            UserCompany(
                user_id=owner.id,
                company_id=company.id,
                role=UserRole.OWNER.value,
                status=MembershipStatus.ACTIVE.value,
            )
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("The company could not be created.") from None
    except AppError:
        db.rollback()
        raise
    db.refresh(company)
    db.refresh(owner)
    logger.info("company created actor_id=%s company_id=%s", actor.id, company.id)
    return AdminCompanyCreated(
        company=CompanyRead.model_validate(company),
        owner=ProvisionedOwner(
            id=owner.id,
            email=owner.email,
            first_name=owner.first_name,
            last_name=owner.last_name,
            phone=owner.phone,
            status=UserStatus(owner.status),
            linked_existing_user=linked_existing,
        ),
    )


def update_company(db: Session, actor: User, company: Company, data: CompanyUpdate) -> Company:
    if not data.model_fields_set:
        raise BadRequestError("At least one field is required.")
    for field in data.model_fields_set:
        value = getattr(data, field)
        if field == "name" and not isinstance(value, str):
            raise BadRequestError("Company name is required.")
        if field == "status":
            if not isinstance(value, CompanyStatus):
                raise BadRequestError("Status is required.")
            value = value.value
        setattr(company, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise BadRequestError("Company could not be saved.") from None
    db.refresh(company)
    logger.info("company updated actor_id=%s company_id=%s", actor.id, company.id)
    return company


def delete_company(db: Session, actor: User, company: Company) -> None:
    blocked_by = _blocking_records(db, company.id)
    if blocked_by:
        raise ConflictError(
            f"This organisation still has {blocked_by} and cannot be deleted."
        )
    company_id = company.id
    db.delete(company)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("This organisation could not be deleted.") from None
    logger.info("company deleted actor_id=%s company_id=%s", actor.id, company_id)


def _blocking_records(db: Session, company_id: UUID) -> str | None:
    checks = (
        ("contacts", Contact),
        ("leads", Lead),
        ("campaigns", MarketingCampaign),
        ("messages", Message),
        ("pipelines", SalesPipeline),
    )
    found: list[str] = []
    for label, model in checks:
        count = db.scalar(
            select(func.count()).select_from(model).where(model.company_id == company_id)
        )
        if count:
            found.append(label)
    if not found:
        return None
    if len(found) == 1:
        return found[0]
    return ", ".join(found[:-1]) + f", and {found[-1]}"


def _resolve_owner(db: Session, owner: OwnerSeed) -> tuple[User, bool]:
    existing = db.scalar(select(User).where(User.email == owner.normalized_email()))
    if existing is not None:
        return existing, True
    user = User(
        email=owner.normalized_email(),
        password_hash=hash_password(secrets.token_urlsafe(32)),
        first_name=owner.first_name.strip(),
        last_name=owner.last_name.strip(),
        phone=owner.phone,
        status=UserStatus.INVITED.value,
        is_super_admin=False,
    )
    db.add(user)
    db.flush()
    return user, False


def _company_filters(
    search: str | None,
    status: CompanyStatus | None,
    business_type: str | None,
) -> list[ColumnElement[bool]]:
    filters: list[ColumnElement[bool]] = []
    if search is not None and search.strip():
        filters.append(Company.name.ilike(contains_pattern(search.strip()), escape="\\"))
    if status is not None:
        filters.append(Company.status == status.value)
    if business_type is not None and business_type.strip():
        filters.append(Company.business_type == business_type.strip())
    return filters


def _primary_owners(
    db: Session,
    company_ids: list[UUID],
) -> dict[UUID, tuple[str, str]]:
    if not company_ids:
        return {}
    rows = db.execute(
        select(
            UserCompany.company_id,
            User.first_name,
            User.last_name,
            User.email,
        )
        .join(User, User.id == UserCompany.user_id)
        .where(
            UserCompany.company_id.in_(company_ids),
            UserCompany.role == UserRole.OWNER.value,
        )
        .order_by(UserCompany.company_id, UserCompany.created_at, UserCompany.id)
    ).all()
    found: dict[UUID, tuple[str, str]] = {}
    for company_id, first_name, last_name, email in rows:
        if isinstance(company_id, UUID) and company_id not in found:
            found[company_id] = (f"{first_name} {last_name}", str(email))
    return found

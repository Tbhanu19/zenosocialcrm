"""Company authorization.

Existence and access are separate checks. Future company-scoped modules should
call authorize_company_access instead of loading a company by id alone.
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.permissions import CompanyStatus, MembershipStatus, UserRole
from app.models.company import Company
from app.models.user import User
from app.models.user_company import UserCompany
from app.schemas.company import AvailableCompanyRead


@dataclass(frozen=True)
class CompanyAccess:
    company: Company
    role: UserRole


def authorize_company_access(
    db: Session,
    user: User,
    company_id: UUID,
    *,
    required_roles: frozenset[UserRole] | None = None,
) -> CompanyAccess:
    """Return the company only when this user may access it.

    A missing company is 404. A company that exists but is outside the user's
    memberships is 403. Super admin access is decided in this function only.
    """
    company = db.get(Company, company_id)
    if company is None:
        raise NotFoundError("Company not found.")

    if user.is_super_admin:
        return CompanyAccess(company=company, role=UserRole.SUPER_ADMIN)

    if company.status != CompanyStatus.ACTIVE.value:
        raise ForbiddenError()

    membership = db.scalar(
        select(UserCompany).where(
            UserCompany.user_id == user.id,
            UserCompany.company_id == company_id,
            UserCompany.status == MembershipStatus.ACTIVE.value,
        )
    )
    if membership is None:
        raise ForbiddenError()

    role = UserRole(membership.role)
    if required_roles is not None and role not in required_roles:
        raise ForbiddenError("Your role does not allow this action.")
    return CompanyAccess(company=company, role=role)


def list_accessible_companies(db: Session, user: User) -> list[AvailableCompanyRead]:
    """Load every company the user may enter in a single query."""
    if user.is_super_admin:
        companies = db.scalars(select(Company).order_by(Company.name, Company.id)).all()
        return [
            AvailableCompanyRead(
                id=company.id,
                name=company.name,
                role=UserRole.SUPER_ADMIN,
                status=CompanyStatus(company.status),
            )
            for company in companies
        ]

    rows = db.execute(
        select(Company, UserCompany.role)
        .join(UserCompany, UserCompany.company_id == Company.id)
        .where(
            UserCompany.user_id == user.id,
            UserCompany.status == MembershipStatus.ACTIVE.value,
            Company.status == CompanyStatus.ACTIVE.value,
        )
        .order_by(Company.name, Company.id)
    ).all()
    return [
        AvailableCompanyRead(
            id=company.id,
            name=company.name,
            role=UserRole(role),
            status=CompanyStatus(company.status),
        )
        for company, role in rows
    ]

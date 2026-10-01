"""Company membership creation."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.permissions import COMPANY_MEMBERSHIP_ROLES
from app.models.company import Company
from app.models.user import User
from app.models.user_company import UserCompany
from app.schemas.company import MembershipCreate


def add_membership(db: Session, data: MembershipCreate) -> UserCompany:
    if data.role not in COMPANY_MEMBERSHIP_ROLES:
        raise BadRequestError("That role cannot be assigned as a company membership.")

    user_exists = db.scalar(select(User.id).where(User.id == data.user_id))
    if user_exists is None:
        raise NotFoundError("User not found.")
    company_exists = db.scalar(select(Company.id).where(Company.id == data.company_id))
    if company_exists is None:
        raise NotFoundError("Company not found.")

    existing = db.scalar(
        select(UserCompany.id).where(
            UserCompany.user_id == data.user_id,
            UserCompany.company_id == data.company_id,
        )
    )
    if existing is not None:
        raise ConflictError("This user already has a membership for that company.")

    membership = UserCompany(
        user_id=data.user_id,
        company_id=data.company_id,
        role=data.role.value,
        status=data.status.value,
    )
    db.add(membership)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("This user already has a membership for that company.") from None
    db.refresh(membership)
    return membership

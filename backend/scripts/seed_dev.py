"""Local development accounts.

Refuses to run unless ENVIRONMENT=development.
DEV_PASSWORD is a local sample credential, not a production secret.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.permissions import UserRole
from app.db.session import SessionLocal
from app.models.company import Company
from app.models.user import User
from app.models.user_company import UserCompany
from app.schemas.company import CompanyCreate, MembershipCreate
from app.schemas.user import UserCreate
from app.services.auth_service import create_user
from app.services.company_service import create_company
from app.services.membership_service import add_membership

DEV_PASSWORD = "dev-only-password"


def main() -> None:
    settings = get_settings()
    if settings.environment != "development":
        raise SystemExit("seed_dev.py only runs when ENVIRONMENT=development.")

    db = SessionLocal()
    try:
        admin = _ensure_user(db, "root@example.com", "Root", "Admin", is_super_admin=True)
        owner = _ensure_user(db, "owner@example.com", "Olivia", "Owner", is_super_admin=False)
        employee = _ensure_user(
            db,
            "employee@example.com",
            "Evan",
            "Employee",
            is_super_admin=False,
        )
        company_a = _ensure_company(db, "Company A")
        company_b = _ensure_company(db, "Company B")
        _ensure_membership(db, owner, company_a, UserRole.OWNER)
        _ensure_membership(db, owner, company_b, UserRole.OWNER)
        _ensure_membership(db, employee, company_a, UserRole.EMPLOYEE)
        print("Development accounts are ready.")
        print(f"super admin: {admin.email}")
        print(f"owner: {owner.email}")
        print(f"employee: {employee.email}")
    finally:
        db.close()


def _ensure_user(
    db: Session,
    email: str,
    first_name: str,
    last_name: str,
    *,
    is_super_admin: bool,
) -> User:
    existing = db.scalar(select(User).where(User.email == email))
    if existing is not None:
        return existing
    return create_user(
        db,
        UserCreate(
            email=email,
            password=DEV_PASSWORD,
            first_name=first_name,
            last_name=last_name,
            is_super_admin=is_super_admin,
        ),
    )


def _ensure_company(db: Session, name: str) -> Company:
    existing = db.scalar(select(Company).where(Company.name == name))
    if existing is not None:
        return existing
    return create_company(db, CompanyCreate(name=name, business_type="local_service"))


def _ensure_membership(db: Session, user: User, company: Company, role: UserRole) -> None:
    existing = db.scalar(
        select(UserCompany.id).where(
            UserCompany.user_id == user.id,
            UserCompany.company_id == company.id,
        )
    )
    if existing is not None:
        return
    add_membership(
        db,
        MembershipCreate(user_id=user.id, company_id=company.id, role=role),
    )


if __name__ == "__main__":
    main()

"""Company records and user-company memberships."""

import uuid

import pytest
from pydantic import ValidationError
from sqlalchemy import UniqueConstraint
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.permissions import UserRole, UserStatus
from app.models.company import Company
from app.models.user import User
from app.models.user_company import UserCompany
from app.schemas.company import CompanyCreate, MembershipCreate
from app.services.authorization_service import list_accessible_companies
from app.services.company_service import create_company
from app.services.membership_service import add_membership
from tests.conftest import make_company, make_membership, make_user


def test_create_company(db: Session) -> None:
    company = create_company(
        db,
        CompanyCreate(
            name="  ABC Car Wash  ",
            business_type="car_wash",
            phone="2145550199",
            email="hello@abccarwash.example",
            city="Austin",
            state="TX",
            zip_code="78701",
        ),
    )
    assert company.name == "ABC Car Wash"
    assert company.phone == "(214) 555-0199"
    assert company.email == "hello@abccarwash.example"
    assert company.id is not None


def test_blank_company_name_is_rejected() -> None:
    with pytest.raises(ValidationError):
        CompanyCreate(name="   ")


def test_empty_company_name_cannot_be_stored(db: Session) -> None:
    db.add(
        Company(
            name="   ",
            status="active",
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_invalid_company_status_is_rejected(db: Session) -> None:
    db.add(Company(name="Valid Name", status="archived"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_user_can_belong_to_multiple_companies(db: Session) -> None:
    owner = make_user(db, email="owner@example.com")
    company_a = make_company(db, name="Company A")
    company_b = make_company(db, name="Company B")
    make_membership(db, owner, company_a, UserRole.OWNER)
    make_membership(db, owner, company_b, UserRole.OWNER)

    available = list_accessible_companies(db, owner)
    assert [(item.name, item.role) for item in available] == [
        ("Company A", UserRole.OWNER),
        ("Company B", UserRole.OWNER),
    ]


def test_duplicate_membership_is_rejected(db: Session) -> None:
    user = make_user(db)
    company = make_company(db)
    make_membership(db, user, company, UserRole.EMPLOYEE)
    with pytest.raises(ConflictError):
        make_membership(db, user, company, UserRole.COMPANY_MANAGER)


def test_duplicate_membership_is_rejected_by_the_database(db: Session) -> None:
    user = make_user(db)
    company = make_company(db)
    make_membership(db, user, company, UserRole.EMPLOYEE)
    db.add(
        UserCompany(
            user_id=user.id,
            company_id=company.id,
            role=UserRole.OWNER.value,
            status="active",
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_super_admin_cannot_be_stored_as_a_company_role(db: Session) -> None:
    user = make_user(db, is_super_admin=True, email="root@example.com")
    company = make_company(db)
    with pytest.raises(BadRequestError):
        add_membership(
            db,
            MembershipCreate(
                user_id=user.id,
                company_id=company.id,
                role=UserRole.SUPER_ADMIN,
            ),
        )

    db.add(
        UserCompany(
            user_id=user.id,
            company_id=company.id,
            role=UserRole.SUPER_ADMIN.value,
            status="active",
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_unknown_role_is_rejected_by_the_database(db: Session) -> None:
    user = make_user(db)
    company = make_company(db)
    db.add(
        UserCompany(
            user_id=user.id,
            company_id=company.id,
            role="intern",
            status="active",
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_membership_requires_a_real_company(db: Session) -> None:
    user = make_user(db)
    missing_company_id = uuid.uuid4()
    with pytest.raises(NotFoundError):
        add_membership(
            db,
            MembershipCreate(
                user_id=user.id,
                company_id=missing_company_id,
                role=UserRole.EMPLOYEE,
            ),
        )

    db.add(
        UserCompany(
            user_id=user.id,
            company_id=missing_company_id,
            role=UserRole.EMPLOYEE.value,
            status="active",
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_membership_requires_a_real_user(db: Session) -> None:
    company = make_company(db)
    with pytest.raises(NotFoundError):
        add_membership(
            db,
            MembershipCreate(
                user_id=uuid.uuid4(),
                company_id=company.id,
                role=UserRole.EMPLOYEE,
            ),
        )


def test_invalid_user_status_is_rejected(db: Session) -> None:
    db.add(
        User(
            email="ada@example.com",
            password_hash="hash",
            first_name="Ada",
            last_name="Lovelace",
            status="deleted",
            is_super_admin=False,
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_phase1_indexes_and_unique_membership() -> None:
    index_names = {index.name for index in UserCompany.__table__.indexes}
    assert "ix_user_companies_company_id" in index_names
    assert "ix_user_companies_role" in index_names
    unique_names = {
        constraint.name
        for constraint in UserCompany.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert "uq_user_companies_user_company" in unique_names

    user_indexes = {index.name for index in User.__table__.indexes}
    company_indexes = {index.name for index in Company.__table__.indexes}
    assert "ix_users_status" in user_indexes
    assert "ix_companies_name" in company_indexes
    assert "ix_companies_status" in company_indexes


def test_user_status_enum_round_trip(db: Session) -> None:
    invited = make_user(db, email="invited@example.com", status=UserStatus.INVITED)
    assert invited.status == UserStatus.INVITED.value

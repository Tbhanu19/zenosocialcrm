"""Shared fixtures for the Phase 1 backend tests."""

# Environment must be set before the application is imported.
# ruff: noqa: E402

import os

os.environ["DATABASE_URL"] = "sqlite+pysqlite://"
os.environ["SECRET_KEY"] = "test-secret-key-at-least-32-characters"
os.environ["ENVIRONMENT"] = "test"
os.environ["CORS_ORIGINS"] = "http://localhost:5173"
os.environ["JWT_EXPIRE_MINUTES"] = "60"

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.login_throttle import login_throttle
from app.core.permissions import CompanyStatus, MembershipStatus, UserRole, UserStatus
from app.core.security import create_access_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.company import Company
from app.models.user import User
from app.models.user_company import UserCompany
from app.schemas.company import CompanyCreate, MembershipCreate
from app.schemas.user import UserCreate
from app.services.auth_service import create_user
from app.services.company_service import create_company
from app.services.membership_service import add_membership

get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _reset_login_throttle() -> Generator[None, None, None]:
    login_throttle.reset()
    yield
    login_throttle.reset()


@pytest.fixture
def engine() -> Generator[Engine, None, None]:
    test_engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(test_engine, "connect")
    def _enable_foreign_keys(dbapi_connection: object, _connection_record: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(test_engine)
    yield test_engine
    Base.metadata.drop_all(test_engine)
    test_engine.dispose()


@pytest.fixture
def db(engine: Engine) -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(
        bind=connection,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    session = factory()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def auth_header(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id, user.token_version)}"}


def make_user(
    db: Session,
    *,
    email: str = "ada@example.com",
    password: str = "password123",
    first_name: str = "Ada",
    last_name: str = "Lovelace",
    status: UserStatus = UserStatus.ACTIVE,
    is_super_admin: bool = False,
) -> User:
    return create_user(
        db,
        UserCreate(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            status=status,
            is_super_admin=is_super_admin,
        ),
    )


def make_company(
    db: Session,
    *,
    name: str = "Northwind Wash",
    phone: str | None = "2145550100",
    status: CompanyStatus = CompanyStatus.ACTIVE,
) -> Company:
    return create_company(
        db,
        CompanyCreate(name=name, phone=phone, business_type="car_wash", status=status),
    )


def make_membership(
    db: Session,
    user: User,
    company: Company,
    role: UserRole,
    *,
    status: MembershipStatus = MembershipStatus.ACTIVE,
) -> UserCompany:
    return add_membership(
        db,
        MembershipCreate(
            user_id=user.id,
            company_id=company.id,
            role=role,
            status=status,
        ),
    )

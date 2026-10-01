"""User creation, password handling, and current-user responses."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.login_throttle import login_throttle
from app.core.permissions import UserStatus
from app.core.security import verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserRead
from app.services.auth_service import authenticate
from tests.conftest import auth_header, make_company, make_user


def test_create_user_stores_a_secure_password_hash(db: Session) -> None:
    user = make_user(db, email="ada@example.com", password="password123")

    assert user.email == "ada@example.com"
    assert user.password_hash != "password123"
    assert user.password_hash.startswith("$argon2")
    assert verify_password("password123", user.password_hash)
    assert verify_password("wrong-password", user.password_hash) is False
    assert "password" not in repr(user)


def test_email_is_stored_in_normalized_form(db: Session) -> None:
    user = make_user(db, email="Ada@Example.com")
    assert user.email == "ada@example.com"


def test_duplicate_email_is_rejected_by_the_service(db: Session) -> None:
    make_user(db, email="ada@example.com")
    with pytest.raises(ConflictError):
        make_user(db, email="ADA@example.com")


def test_duplicate_email_is_rejected_by_the_database(db: Session) -> None:
    make_user(db, email="ada@example.com")
    db.add(
        User(
            email="ada@example.com",
            password_hash="not-a-login-hash",
            first_name="Grace",
            last_name="Hopper",
            status=UserStatus.ACTIVE.value,
            is_super_admin=False,
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_blank_name_is_rejected() -> None:
    with pytest.raises(ValidationError):
        UserCreate(
            email="ada@example.com",
            password="password123",
            first_name="   ",
            last_name="Lovelace",
        )


def test_login_and_me_never_return_the_password_hash(client: TestClient, db: Session) -> None:
    make_user(db, email="ada@example.com", password="password123")

    login = client.post(
        "/api/auth/login",
        json={"email": "ada@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    body = login.json()
    assert body["token_type"] == "bearer"
    assert "password" not in body
    assert "$argon2" not in login.text

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    payload = me.json()
    assert payload["email"] == "ada@example.com"
    assert "password" not in payload
    assert "password_hash" not in payload
    assert "$argon2" not in me.text
    assert set(payload) == {
        "id",
        "email",
        "first_name",
        "last_name",
        "phone",
        "status",
        "is_super_admin",
        "created_at",
        "updated_at",
    }


def test_user_read_schema_has_no_password_fields() -> None:
    assert "password" not in UserRead.model_fields
    assert "password_hash" not in UserRead.model_fields


def test_invalid_login_does_not_echo_the_password(client: TestClient, db: Session) -> None:
    make_user(db, email="ada@example.com", password="password123")
    response = client.post(
        "/api/auth/login",
        json={"email": "ada@example.com", "password": "not-the-password"},
    )
    assert response.status_code == 401
    assert "not-the-password" not in response.text
    assert "$argon2" not in response.text


def test_validation_error_does_not_echo_the_password(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"email": "not-an-email", "password": "super-secret-value"},
    )
    assert response.status_code == 422
    assert "super-secret-value" not in response.text


def test_missing_token_is_unauthorized(client: TestClient) -> None:
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_inactive_user_cannot_authenticate(db: Session) -> None:
    make_user(db, email="ada@example.com", status=UserStatus.INACTIVE)
    with pytest.raises(UnauthorizedError):
        authenticate(db, "ada@example.com", "password123")


def test_health(client: TestClient) -> None:
    live = client.get("/api/health/live")
    assert live.status_code == 200
    assert live.json() == {"status": "ok"}
    assert "database" not in live.json()
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_production_hides_api_docs() -> None:
    from app.core.config import Settings

    production = Settings(
        environment="production",
        secret_key="production-secret-key-at-least-32-characters",
        cors_origins="https://app.example.com",
        database_url="mysql+pymysql://user:pass@localhost:3306/zenosocialcrm",
    )
    assert production.expose_api_docs is False
    assert production.is_production is True


def test_cors_origins_are_explicit() -> None:
    origins = get_settings_origins()
    assert origins
    assert "*" not in origins


def get_settings_origins() -> list[str]:
    from app.core.config import get_settings

    return get_settings().cors_origin_list


def test_mysql_duplicate_key_name_is_read_without_the_value() -> None:
    from app.core.exceptions import _constraint_name

    class _DriverError(Exception):
        pass

    driver_error = _DriverError(
        1062,
        "Duplicate entry 'ada@example.com' for key 'users.uq_users_email'",
    )
    constraint = _constraint_name(IntegrityError("INSERT", {}, driver_error))
    assert constraint == "uq_users_email"


def test_login_failures_share_one_message(client: TestClient, db: Session) -> None:
    make_user(db, email="ada@example.com", password="password123", status=UserStatus.INACTIVE)
    make_user(db, email="invite@example.com", password="password123", status=UserStatus.INVITED)
    make_user(db, email="active@example.com", password="password123")

    unknown = client.post(
        "/api/auth/login",
        json={"email": "missing@example.com", "password": "password123"},
    )
    inactive = client.post(
        "/api/auth/login",
        json={"email": "ada@example.com", "password": "password123"},
    )
    invited = client.post(
        "/api/auth/login",
        json={"email": "invite@example.com", "password": "password123"},
    )
    wrong_password = client.post(
        "/api/auth/login",
        json={"email": "active@example.com", "password": "not-the-password"},
    )
    assert unknown.status_code == 401
    assert unknown.json() == inactive.json() == invited.json() == wrong_password.json()
    assert unknown.json()["error"]["message"] == "Invalid email or password."
    assert "not-the-password" not in wrong_password.text
    assert "inactive" not in unknown.text
    assert "invited" not in invited.text


def test_failed_login_log_omits_the_password(
    client: TestClient,
    db: Session,
    caplog: pytest.LogCaptureFixture,
) -> None:
    make_user(db, email="ada@example.com", password="password123")
    with caplog.at_level("INFO", logger="zenosocialcrm.auth"):
        client.post(
            "/api/auth/login",
            json={"email": "ada@example.com", "password": "not-the-password"},
        )
    assert "bad_password" in caplog.text
    assert "not-the-password" not in caplog.text


def test_login_ignores_client_supplied_role_and_company(client: TestClient, db: Session) -> None:
    make_user(db, email="ada@example.com", password="password123")
    company = make_company(db)
    login = client.post(
        "/api/auth/login",
        json={
            "email": "ada@example.com",
            "password": "password123",
            "role": "super_admin",
            "is_super_admin": True,
            "company_id": str(company.id),
        },
    )
    assert login.status_code == 200
    me = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["is_super_admin"] is False


def test_missing_and_malformed_login_are_rejected(client: TestClient) -> None:
    missing = client.post("/api/auth/login", json={})
    assert missing.status_code == 422
    email_only = client.post("/api/auth/login", json={"email": "ada@example.com"})
    assert email_only.status_code == 422
    password_only = client.post("/api/auth/login", json={"password": "password123"})
    assert password_only.status_code == 422
    malformed = client.post(
        "/api/auth/login",
        content="not-json",
        headers={"Content-Type": "application/json"},
    )
    assert malformed.status_code == 422


def test_expired_and_malformed_tokens_are_rejected(client: TestClient, db: Session) -> None:
    user = make_user(db)
    settings = get_settings()
    expired = jwt.encode(
        {
            "sub": str(user.id),
            "ver": user.token_version,
            "exp": datetime.now(UTC) - timedelta(minutes=5),
        },
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )
    expired_response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert expired_response.status_code == 401
    malformed = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-token"})
    assert malformed.status_code == 401
    missing_version = jwt.encode(
        {"sub": str(user.id), "exp": datetime.now(UTC) + timedelta(minutes=5)},
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )
    unsigned_version = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {missing_version}"},
    )
    assert unsigned_version.status_code == 401


def test_logout_invalidates_the_access_token(client: TestClient, db: Session) -> None:
    make_user(db, email="ada@example.com", password="password123")
    login = client.post(
        "/api/auth/login",
        json={"email": "ada@example.com", "password": "password123"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    logout = client.post("/api/auth/logout", headers=headers)
    assert logout.status_code == 204
    assert logout.content == b""
    assert client.get("/api/auth/me", headers=headers).status_code == 401
    assert client.post("/api/auth/logout").status_code == 401
    again = client.post(
        "/api/auth/login",
        json={"email": "ada@example.com", "password": "password123"},
    )
    assert again.status_code == 200
    assert client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {again.json()['access_token']}"},
    ).status_code == 200


def test_repeated_login_failures_are_rate_limited(client: TestClient, db: Session) -> None:
    make_user(db, email="ada@example.com", password="password123")
    previous_limit = login_throttle.max_identity_failures
    login_throttle.max_identity_failures = 2
    payload = {"email": "ada@example.com", "password": "not-the-password"}
    try:
        assert client.post("/api/auth/login", json=payload).status_code == 401
        assert client.post("/api/auth/login", json=payload).status_code == 401
        blocked = client.post("/api/auth/login", json=payload)
        assert blocked.status_code == 429
        assert "not-the-password" not in blocked.text
    finally:
        login_throttle.max_identity_failures = previous_limit


def test_current_user_query_count_stays_at_one(
    client: TestClient,
    db: Session,
    engine: Engine,
) -> None:
    user = make_user(db)
    headers = auth_header(user)
    statements: list[str] = []

    def before_cursor_execute(
        _conn: object,
        _cursor: object,
        statement: str,
        _parameters: object,
        _context: object,
        _executemany: bool,
    ) -> None:
        if statement.lstrip().lower().startswith("select"):
            statements.append(" ".join(statement.split()))

    db.expire_all()
    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    try:
        response = client.get("/api/auth/me", headers=headers)
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)
    assert response.status_code == 200
    assert len(statements) == 1, statements


def test_auth_header_helper_can_read_current_user(client: TestClient, db: Session) -> None:
    user = make_user(db)
    response = client.get("/api/auth/me", headers=auth_header(user))
    assert response.status_code == 200
    assert response.json()["id"] == str(user.id)


def test_current_user_can_update_name_email_and_phone(client: TestClient, db: Session) -> None:
    user = make_user(db, email="ada@example.com", password="password123")
    other = make_user(db, email="grace@example.com")
    headers = auth_header(user)

    updated = client.patch(
        "/api/auth/me",
        headers=headers,
        json={
            "first_name": " Augusta ",
            "last_name": "King",
            "email": "ADA@example.com",
            "phone": "2145550100",
        },
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["first_name"] == "Augusta"
    assert body["last_name"] == "King"
    assert body["email"] == "ada@example.com"
    assert body["phone"] == "(214) 555-0100"
    assert body["is_super_admin"] is False
    assert "password" not in body

    conflict = client.patch(
        "/api/auth/me",
        headers=headers,
        json={
            "first_name": "Augusta",
            "last_name": "King",
            "email": other.email,
            "phone": "",
        },
    )
    assert conflict.status_code == 409
    assert user.email == "ada@example.com"

"""Company administration and company-scoped user management."""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.permissions import UserRole, UserStatus
from app.models.company import Company
from app.models.user import User
from tests.conftest import auth_header, make_company, make_membership, make_user

OWNER_BODY = {
    "first_name": "John",
    "last_name": "Smith",
    "email": "john@example.com",
    "phone": "2145550199",
}


def _company_body(name: str = "ABC Car Wash", **owner_overrides: str) -> dict[str, object]:
    owner = {**OWNER_BODY, **owner_overrides}
    return {
        "name": name,
        "business_type": "car_wash",
        "phone": "2145550100",
        "email": "hello@abc.example",
        "status": "active",
        "owner": owner,
    }


def _selects(engine: Engine, action: Callable[[], object]) -> list[str]:
    statements: list[str] = []

    def before(
        _conn: object,
        _cursor: object,
        statement: str,
        _parameters: object,
        _context: object,
        _executemany: bool,
    ) -> None:
        if statement.lstrip().lower().startswith("select"):
            statements.append(" ".join(statement.split()))

    event.listen(engine, "before_cursor_execute", before)
    try:
        action()
    finally:
        event.remove(engine, "before_cursor_execute", before)
    return statements


@pytest.mark.parametrize(
    "role",
    [UserRole.OWNER, UserRole.COMPANY_MANAGER, UserRole.MARKETING_MANAGER, UserRole.EMPLOYEE],
)
def test_only_super_admin_can_create_a_company(
    client: TestClient,
    db: Session,
    role: UserRole,
) -> None:
    actor = make_user(db, email=f"{role.value}-create@example.com")
    company = make_company(db, name=f"{role.value} home")
    make_membership(db, actor, company, role)
    response = client.post(
        "/api/admin/companies",
        headers=auth_header(actor),
        json=_company_body(),
    )
    assert response.status_code == 403
    remaining = db.scalar(
        select(func.count()).select_from(Company).where(Company.name == "ABC Car Wash")
    )
    assert remaining == 0


def test_super_admin_creates_company_and_invited_owner(client: TestClient, db: Session) -> None:
    admin = make_user(db, email="root-create@example.com", is_super_admin=True)
    response = client.post(
        "/api/admin/companies",
        headers=auth_header(admin),
        json=_company_body(),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["company"]["name"] == "ABC Car Wash"
    assert body["owner"]["email"] == "john@example.com"
    assert body["owner"]["status"] == UserStatus.INVITED.value
    assert body["owner"]["linked_existing_user"] is False
    assert "password" not in response.text
    login = client.post(
        "/api/auth/login",
        json={"email": "john@example.com", "password": "password123"},
    )
    assert login.status_code == 401


def test_existing_user_becomes_owner_without_being_overwritten(
    client: TestClient,
    db: Session,
) -> None:
    admin = make_user(db, email="root-link@example.com", is_super_admin=True)
    existing = make_user(db, email="john@example.com", first_name="Jonathan", last_name="Existing")
    before = db.scalar(select(func.count()).select_from(User))
    response = client.post(
        "/api/admin/companies",
        headers=auth_header(admin),
        json=_company_body(first_name="Different", last_name="Name"),
    )
    assert response.status_code == 201
    assert response.json()["owner"]["linked_existing_user"] is True
    assert response.json()["owner"]["first_name"] == "Jonathan"
    db.refresh(existing)
    assert existing.first_name == "Jonathan"
    assert existing.last_name == "Existing"
    assert db.scalar(select(func.count()).select_from(User)) == before


def test_super_admin_cannot_be_assigned_as_the_initial_owner(
    client: TestClient,
    db: Session,
) -> None:
    admin = make_user(db, email="root-owner@example.com", is_super_admin=True)
    response = client.post(
        "/api/admin/companies",
        headers=auth_header(admin),
        json=_company_body("Rolled Back Wash", email="root-owner@example.com"),
    )
    assert response.status_code == 409
    remaining = db.scalar(
        select(func.count()).select_from(Company).where(Company.name == "Rolled Back Wash")
    )
    assert remaining == 0


def test_company_list_is_super_admin_only_and_paginated(client: TestClient, db: Session) -> None:
    admin = make_user(db, email="root-list@example.com", is_super_admin=True)
    owner = make_user(db, email="owner-list@example.com")
    for index in range(1, 4):
        company = make_company(db, name=f"Car Shop {index:02d}")
        make_membership(db, owner, company, UserRole.OWNER)
    make_company(db, name="Hotel One")
    denied = client.get("/api/admin/companies", headers=auth_header(owner))
    assert denied.status_code == 403

    first = client.get(
        "/api/admin/companies",
        headers=auth_header(admin),
        params={"search": "car", "page_size": 2, "page": 1},
    )
    assert first.status_code == 200
    payload = first.json()
    assert payload["total"] == 3
    assert payload["total_pages"] == 2
    assert len(payload["items"]) == 2
    assert payload["items"][0]["owner_name"] == "Ada Lovelace"
    second = client.get(
        "/api/admin/companies",
        headers=auth_header(admin),
        params={"search": "car", "page_size": 2, "page": 2},
    )
    assert len(second.json()["items"]) == 1
    assert client.get(
        "/api/admin/companies",
        headers=auth_header(admin),
        params={"page": 0},
    ).status_code == 422
    assert client.get(
        "/api/admin/companies",
        headers=auth_header(admin),
        params={"page": -1},
    ).status_code == 422
    assert client.get(
        "/api/admin/companies",
        headers=auth_header(admin),
        params={"page_size": 101},
    ).status_code == 422
    assert client.get(
        "/api/admin/companies",
        headers=auth_header(admin),
        params={"page_size": 100},
    ).status_code == 200


def test_super_admin_can_edit_company_and_members_cannot(
    client: TestClient,
    db: Session,
) -> None:
    admin = make_user(db, email="root-edit@example.com", is_super_admin=True)
    owner = make_user(db, email="owner-edit@example.com")
    company = make_company(db, name="Editable Co")
    make_membership(db, owner, company, UserRole.OWNER)
    denied = client.patch(
        f"/api/admin/companies/{company.id}",
        headers=auth_header(owner),
        json={"name": "Stolen"},
    )
    assert denied.status_code == 403
    updated = client.patch(
        f"/api/admin/companies/{company.id}",
        headers=auth_header(admin),
        json={"name": "Renamed Co", "status": "inactive"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Renamed Co"
    assert updated.json()["status"] == "inactive"
    assert updated.json()["id"] == str(company.id)
    detail = client.get(f"/api/admin/companies/{company.id}", headers=auth_header(admin))
    assert detail.status_code == 200
    assert detail.json()["counts"]["owners"] == 1
    hidden = client.get(f"/api/admin/companies/{company.id}", headers=auth_header(owner))
    assert hidden.status_code == 403


def test_company_list_query_count_does_not_grow_with_owners(
    client: TestClient,
    db: Session,
    engine: Engine,
) -> None:
    admin = make_user(db, email="root-count@example.com", is_super_admin=True)
    owner = make_user(db, email="owner-count@example.com")
    first = make_company(db, name="Counted 01")
    make_membership(db, owner, first, UserRole.OWNER)
    headers = auth_header(admin)

    def load() -> None:
        response = client.get("/api/admin/companies", headers=headers, params={"page_size": 20})
        assert response.status_code == 200

    db.expire_all()
    one = _selects(engine, load)
    for index in range(2, 21):
        company = make_company(db, name=f"Counted {index:02d}")
        make_membership(db, owner, company, UserRole.OWNER)
    db.expire_all()
    many = _selects(engine, load)
    assert len(one) == len(many)
    assert len(many) <= 4, many


def test_owner_sees_only_the_selected_companys_users(client: TestClient, db: Session) -> None:
    john = make_user(db, email="john-owner@example.com", first_name="John", last_name="Owner")
    employee_a = make_user(db, email="employee-a@example.com", first_name="Amy", last_name="A")
    employee_b = make_user(db, email="employee-b@example.com", first_name="Ben", last_name="B")
    company_a = make_company(db, name="Company A")
    company_b = make_company(db, name="Company B")
    make_membership(db, john, company_a, UserRole.OWNER)
    make_membership(db, john, company_b, UserRole.OWNER)
    make_membership(db, employee_a, company_a, UserRole.EMPLOYEE)
    make_membership(db, employee_b, company_b, UserRole.EMPLOYEE)
    headers = auth_header(john)

    company_a_users = client.get(f"/api/companies/{company_a.id}/users", headers=headers)
    assert company_a_users.status_code == 200
    emails = {item["email"] for item in company_a_users.json()["items"]}
    assert "employee-a@example.com" in emails
    assert "employee-b@example.com" not in emails

    company_b_users = client.get(f"/api/companies/{company_b.id}/users", headers=headers)
    emails_b = {item["email"] for item in company_b_users.json()["items"]}
    assert "employee-b@example.com" in emails_b
    assert "employee-a@example.com" not in emails_b


@pytest.mark.parametrize("role", [UserRole.MARKETING_MANAGER, UserRole.EMPLOYEE])
def test_non_managers_cannot_add_users(client: TestClient, db: Session, role: UserRole) -> None:
    actor = make_user(db, email=f"{role.value}-add@example.com")
    company = make_company(db)
    make_membership(db, actor, company, role)
    response = client.post(
        f"/api/companies/{company.id}/users",
        headers=auth_header(actor),
        json={
            "first_name": "New",
            "last_name": "Person",
            "email": "new-person@example.com",
            "role": "employee",
        },
    )
    assert response.status_code == 403
    assert "new-person@example.com" not in response.text


def test_owner_can_add_an_employee_but_not_a_super_admin_or_owner(
    client: TestClient,
    db: Session,
) -> None:
    owner = make_user(db, email="owner-add@example.com")
    company = make_company(db, name="Owner Co")
    other = make_company(db, name="Other Co")
    make_membership(db, owner, company, UserRole.OWNER)
    headers = auth_header(owner)
    created = client.post(
        f"/api/companies/{company.id}/users",
        headers=headers,
        json={
            "first_name": "Eve",
            "last_name": "Employee",
            "email": "eve@example.com",
            "role": "employee",
        },
    )
    assert created.status_code == 201
    assert created.json()["user_status"] == "invited"
    assert created.json()["role"] == "employee"
    assert "password" not in created.text
    for role in ("super_admin", "owner"):
        denied = client.post(
            f"/api/companies/{company.id}/users",
            headers=headers,
            json={
                "first_name": "Nope",
                "last_name": "Role",
                "email": f"{role}@example.com",
                "role": role,
                "company_id": str(other.id),
            },
        )
        assert denied.status_code == 403
    foreign = client.post(
        f"/api/companies/{other.id}/users",
        headers=headers,
        json={
            "first_name": "Foreign",
            "last_name": "User",
            "email": "foreign@example.com",
            "role": "employee",
        },
    )
    assert foreign.status_code == 403
    assert "foreign@example.com" not in foreign.text


def test_company_manager_role_limits_and_cross_company_edit(
    client: TestClient,
    db: Session,
) -> None:
    manager = make_user(db, email="manager-edit@example.com")
    company_a = make_company(db, name="Managed A")
    company_b = make_company(db, name="Managed B")
    employee = make_user(db, email="managed-employee@example.com")
    outsider = make_user(db, email="outsider@example.com")
    make_membership(db, manager, company_a, UserRole.COMPANY_MANAGER)
    make_membership(db, employee, company_a, UserRole.EMPLOYEE)
    make_membership(db, outsider, company_b, UserRole.EMPLOYEE)
    headers = auth_header(manager)

    promoted = client.patch(
        f"/api/companies/{company_a.id}/users/{employee.id}",
        headers=headers,
        json={"role": "marketing_manager"},
    )
    assert promoted.status_code == 200
    assert promoted.json()["role"] == "marketing_manager"

    for role in ("owner", "super_admin", "company_manager"):
        denied = client.patch(
            f"/api/companies/{company_a.id}/users/{employee.id}",
            headers=headers,
            json={"role": role},
        )
        assert denied.status_code == 403

    cross_edit = client.patch(
        f"/api/companies/{company_b.id}/users/{outsider.id}",
        headers=headers,
        json={"membership_status": "inactive"},
    )
    assert cross_edit.status_code == 403
    assert "outsider@example.com" not in cross_edit.text
    cross_list = client.get(f"/api/companies/{company_b.id}/users", headers=headers)
    assert cross_list.status_code == 403


def test_deactivating_one_membership_leaves_the_other_company_active(
    client: TestClient,
    db: Session,
) -> None:
    admin = make_user(db, email="root-deactivate@example.com", is_super_admin=True)
    person = make_user(db, email="both@example.com", first_name="Both", last_name="Places")
    company_a = make_company(db, name="Alpha")
    company_b = make_company(db, name="Beta")
    make_membership(db, person, company_a, UserRole.EMPLOYEE)
    make_membership(db, person, company_b, UserRole.EMPLOYEE)
    response = client.patch(
        f"/api/companies/{company_a.id}/users/{person.id}",
        headers=auth_header(admin),
        json={"membership_status": "inactive"},
    )
    assert response.status_code == 200
    assert response.json()["membership_status"] == "inactive"
    other = client.get(
        f"/api/companies/{company_b.id}/users",
        headers=auth_header(admin),
        params={"search": "both"},
    )
    match = next(item for item in other.json()["items"] if item["email"] == "both@example.com")
    assert match["membership_status"] == "active"
    assert person.status == UserStatus.ACTIVE.value


def test_duplicate_membership_is_rejected(client: TestClient, db: Session) -> None:
    admin = make_user(db, email="root-dup@example.com", is_super_admin=True)
    person = make_user(db, email="member@example.com")
    company = make_company(db)
    make_membership(db, person, company, UserRole.EMPLOYEE)
    response = client.post(
        f"/api/companies/{company.id}/users",
        headers=auth_header(admin),
        json={
            "first_name": "Member",
            "last_name": "Again",
            "email": "member@example.com",
            "role": "employee",
        },
    )
    assert response.status_code == 409


def test_user_search_is_server_side(client: TestClient, db: Session) -> None:
    admin = make_user(db, email="root-search@example.com", is_super_admin=True)
    company = make_company(db, name="Search Co")
    make_membership(
        db,
        make_user(db, email="john.search@example.com", first_name="John", last_name="Finder"),
        company,
        UserRole.EMPLOYEE,
    )
    make_membership(
        db,
        make_user(db, email="mary@example.com", first_name="Mary", last_name="Other"),
        company,
        UserRole.EMPLOYEE,
    )
    response = client.get(
        f"/api/companies/{company.id}/users",
        headers=auth_header(admin),
        params={"search": "john", "page_size": 20},
    )
    assert response.status_code == 200
    emails = [item["email"] for item in response.json()["items"]]
    assert emails == ["john.search@example.com"]
    assert response.json()["total"] == 1


def test_user_list_query_count_stays_bounded(
    client: TestClient,
    db: Session,
    engine: Engine,
) -> None:
    admin = make_user(db, email="root-user-count@example.com", is_super_admin=True)
    company = make_company(db, name="Busy Co")
    make_membership(
        db,
        make_user(db, email="person-01@example.com", first_name="Person", last_name="01"),
        company,
        UserRole.EMPLOYEE,
    )
    headers = auth_header(admin)

    def load() -> None:
        response = client.get(
            f"/api/companies/{company.id}/users",
            headers=headers,
            params={"page_size": 20},
        )
        assert response.status_code == 200

    db.expire_all()
    one = _selects(engine, load)
    for index in range(2, 21):
        make_membership(
            db,
            make_user(
                db,
                email=f"person-{index:02d}@example.com",
                first_name="Person",
                last_name=f"{index:02d}",
            ),
            company,
            UserRole.EMPLOYEE,
        )
    db.expire_all()
    many = _selects(engine, load)
    assert len(one) == len(many)
    assert len(many) <= 5, many
    assert client.get(
        f"/api/companies/{company.id}/users",
        headers=headers,
        params={"page_size": 20},
    ).json()["total"] == 20


def test_company_detail_query_count_is_bounded(
    client: TestClient,
    db: Session,
    engine: Engine,
) -> None:
    admin = make_user(db, email="root-detail@example.com", is_super_admin=True)
    company = make_company(db, name="Detail Co")
    for index, role in enumerate(
        (UserRole.OWNER, UserRole.COMPANY_MANAGER, UserRole.EMPLOYEE),
        start=1,
    ):
        make_membership(
            db,
            make_user(db, email=f"detail-{index}@example.com"),
            company,
            role,
        )
    headers = auth_header(admin)

    def load() -> None:
        response = client.get(f"/api/admin/companies/{company.id}", headers=headers)
        assert response.status_code == 200

    db.expire_all()
    statements = _selects(engine, load)
    assert len(statements) <= 3, statements


def test_global_user_directory_is_super_admin_only(client: TestClient, db: Session) -> None:
    admin = make_user(db, email="root-directory@example.com", is_super_admin=True)
    owner = make_user(db, email="owner-directory@example.com")
    company = make_company(db, name="Directory Co")
    make_membership(db, owner, company, UserRole.OWNER)
    denied = client.get("/api/admin/users", headers=auth_header(owner))
    assert denied.status_code == 403
    allowed = client.get(
        "/api/admin/users",
        headers=auth_header(admin),
        params={"search": "owner-directory"},
    )
    assert allowed.status_code == 200
    assert allowed.json()["items"][0]["company_name"] == "Directory Co"
    assert "password" not in allowed.text


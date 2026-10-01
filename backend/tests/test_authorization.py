"""Backend authorization. Company ids from a client never grant access by themselves."""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import Session

from app.api.deps import get_current_company, require_role, require_super_admin
from app.core.exceptions import ForbiddenError
from app.core.permissions import CompanyStatus, MembershipStatus, UserRole
from app.models.company import Company
from app.models.user import User
from app.services.authorization_service import authorize_company_access
from tests.conftest import auth_header, make_company, make_membership, make_user

COMPANY_SCOPED_ROLES = (
    UserRole.OWNER,
    UserRole.COMPANY_MANAGER,
    UserRole.MARKETING_MANAGER,
    UserRole.EMPLOYEE,
)


def _assigned_world(db: Session, role: UserRole) -> tuple[User, Company, Company]:
    user = make_user(db, email=f"{role.value}@example.com")
    assigned = make_company(db, name=f"{role.value} company", phone="2145551000")
    other = make_company(db, name="Secret Company", phone="2145559999")
    make_membership(db, user, assigned, role)
    return user, assigned, other


@pytest.mark.parametrize("role", COMPANY_SCOPED_ROLES)
def test_member_can_access_only_the_assigned_company(
    client: TestClient,
    db: Session,
    role: UserRole,
) -> None:
    user, assigned, other = _assigned_world(db, role)
    headers = auth_header(user)

    allowed = client.get(f"/api/companies/{assigned.id}", headers=headers)
    assert allowed.status_code == 200
    assert allowed.json()["name"] == assigned.name
    assert allowed.json()["role"] == role.value

    denied = client.get(f"/api/companies/{other.id}", headers=headers)
    assert denied.status_code == 403
    assert "Secret Company" not in denied.text
    assert "555-9999" not in denied.text

    available = client.get("/api/companies/available", headers=headers)
    assert available.status_code == 200
    names = [item["name"] for item in available.json()]
    assert names == [assigned.name]


def test_owner_can_access_each_owned_company_and_not_a_third(
    client: TestClient,
    db: Session,
) -> None:
    owner = make_user(db, email="owner@example.com")
    company_a = make_company(db, name="Company A", phone="2145550001")
    company_b = make_company(db, name="Company B", phone="2145550002")
    company_c = make_company(db, name="Company C", phone="2145550003")
    make_membership(db, owner, company_a, UserRole.OWNER)
    make_membership(db, owner, company_b, UserRole.OWNER)
    headers = auth_header(owner)

    assert client.get(f"/api/companies/{company_a.id}", headers=headers).status_code == 200
    assert client.get(f"/api/companies/{company_b.id}", headers=headers).status_code == 200
    denied = client.get(f"/api/companies/{company_c.id}", headers=headers)
    assert denied.status_code == 403
    assert "Company C" not in denied.text
    assert "555-0003" not in denied.text

    available = client.get("/api/companies/available", headers=headers)
    names = [item["name"] for item in available.json()]
    assert names == ["Company A", "Company B"]


def test_super_admin_can_access_every_company_without_a_membership(
    client: TestClient,
    db: Session,
) -> None:
    admin = make_user(db, email="root@example.com", is_super_admin=True)
    company_a = make_company(db, name="Company A")
    company_b = make_company(db, name="Company B", status=CompanyStatus.INACTIVE)
    headers = auth_header(admin)

    assert client.get(f"/api/companies/{company_a.id}", headers=headers).status_code == 200
    inactive = client.get(f"/api/companies/{company_b.id}", headers=headers)
    assert inactive.status_code == 200
    assert inactive.json()["role"] == UserRole.SUPER_ADMIN.value

    available = client.get("/api/companies/available", headers=headers)
    assert available.status_code == 200
    assert [item["name"] for item in available.json()] == ["Company A", "Company B"]
    assert {item["role"] for item in available.json()} == {UserRole.SUPER_ADMIN.value}


def test_missing_company_is_not_found_rather_than_forbidden(
    client: TestClient,
    db: Session,
) -> None:
    user = make_user(db)
    company = make_company(db)
    make_membership(db, user, company, UserRole.EMPLOYEE)
    missing = "11111111-1111-1111-1111-111111111111"
    response = client.get(f"/api/companies/{missing}", headers=auth_header(user))
    assert response.status_code == 404


def test_inactive_membership_does_not_grant_access(client: TestClient, db: Session) -> None:
    user = make_user(db, email="former@example.com")
    company = make_company(db, name="Former Company", phone="2145552222")
    make_membership(db, user, company, UserRole.EMPLOYEE, status=MembershipStatus.INACTIVE)
    response = client.get(f"/api/companies/{company.id}", headers=auth_header(user))
    assert response.status_code == 403
    assert "555-2222" not in response.text


def test_member_cannot_access_an_inactive_company(client: TestClient, db: Session) -> None:
    user = make_user(db, email="manager@example.com")
    company = make_company(db, name="Paused Company", status=CompanyStatus.INACTIVE)
    make_membership(db, user, company, UserRole.COMPANY_MANAGER)
    response = client.get(f"/api/companies/{company.id}", headers=auth_header(user))
    assert response.status_code == 403


def test_service_denies_a_foreign_company_id(db: Session) -> None:
    employee = make_user(db, email="employee@example.com")
    assigned = make_company(db, name="Assigned")
    foreign = make_company(db, name="Foreign", phone="2145557777")
    make_membership(db, employee, assigned, UserRole.EMPLOYEE)

    access = authorize_company_access(db, employee, assigned.id)
    assert access.company.id == assigned.id

    with pytest.raises(ForbiddenError):
        authorize_company_access(db, employee, foreign.id)


def test_company_header_cannot_select_an_unauthorized_company(db: Session) -> None:
    employee = make_user(db, email="employee-header@example.com")
    assigned = make_company(db, name="Assigned Header")
    foreign = make_company(db, name="Foreign Header")
    make_membership(db, employee, assigned, UserRole.EMPLOYEE)

    allowed = get_current_company(x_company_id=assigned.id, db=db, current_user=employee)
    assert allowed.company.id == assigned.id

    with pytest.raises(ForbiddenError):
        get_current_company(x_company_id=foreign.id, db=db, current_user=employee)


def test_require_role_blocks_a_lower_role_and_allows_super_admin(db: Session) -> None:
    employee = make_user(db, email="employee-role@example.com")
    admin = make_user(db, email="root-role@example.com", is_super_admin=True)
    company = make_company(db)
    make_membership(db, employee, company, UserRole.EMPLOYEE)
    owner_only = require_role(UserRole.OWNER)

    with pytest.raises(ForbiddenError):
        owner_only(company_id=company.id, db=db, current_user=employee)

    access = owner_only(company_id=company.id, db=db, current_user=admin)
    assert access.role is UserRole.SUPER_ADMIN


def test_require_super_admin_rejects_a_company_user(db: Session) -> None:
    employee = make_user(db, email="employee-platform@example.com")
    with pytest.raises(ForbiddenError):
        require_super_admin(current_user=employee)


def test_relationships_do_not_load_implicitly(db: Session) -> None:
    user = make_user(db)
    company = make_company(db)
    make_membership(db, user, company, UserRole.OWNER)
    with pytest.raises(InvalidRequestError):
        _ = user.memberships
    with pytest.raises(InvalidRequestError):
        _ = company.memberships


def _select_statements(engine: Engine, action: Callable[[], object]) -> list[str]:
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

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    try:
        action()
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)
    return statements


def test_available_companies_query_count_does_not_grow_with_companies(
    client: TestClient,
    db: Session,
    engine: Engine,
) -> None:
    owner = make_user(db, email="multi@example.com")
    first = make_company(db, name="Company 01")
    make_membership(db, owner, first, UserRole.OWNER)
    headers = auth_header(owner)

    def request_available() -> None:
        response = client.get("/api/companies/available", headers=headers)
        assert response.status_code == 200

    db.expire_all()
    single_company = _select_statements(engine, request_available)

    for index in range(2, 7):
        company = make_company(db, name=f"Company {index:02d}")
        make_membership(db, owner, company, UserRole.OWNER)

    db.expire_all()
    many_companies = _select_statements(engine, request_available)
    assert len(single_company) == len(many_companies)
    assert len(many_companies) == 2, many_companies
    response = client.get("/api/companies/available", headers=headers)
    assert len(response.json()) == 6


def test_employees_cannot_cross_into_each_others_company(client: TestClient, db: Session) -> None:
    employee_a = make_user(db, email="employee-a@example.com")
    employee_b = make_user(db, email="employee-b@example.com")
    company_a = make_company(db, name="Company A", phone="2145551001")
    company_b = make_company(db, name="Company B", phone="2145552002")
    make_membership(db, employee_a, company_a, UserRole.EMPLOYEE)
    make_membership(db, employee_b, company_b, UserRole.EMPLOYEE)

    denied = client.get(f"/api/companies/{company_b.id}", headers=auth_header(employee_a))
    assert denied.status_code == 403
    assert "Company B" not in denied.text
    assert "555-2002" not in denied.text

    available = client.get("/api/companies/available", headers=auth_header(employee_a))
    assert [item["id"] for item in available.json()] == [str(company_a.id)]


def test_company_id_in_header_or_query_cannot_grant_access(client: TestClient, db: Session) -> None:
    employee = make_user(db, email="employee-spoof@example.com")
    assigned = make_company(db, name="Assigned Company")
    foreign = make_company(db, name="Foreign Company", phone="2145553333")
    make_membership(db, employee, assigned, UserRole.EMPLOYEE)
    headers = auth_header(employee)

    by_query = client.get(
        "/api/companies/available",
        headers=headers,
        params={"company_id": str(foreign.id)},
    )
    assert by_query.status_code == 200
    assert [item["id"] for item in by_query.json()] == [str(assigned.id)]

    header_does_not_replace_the_path = client.get(
        f"/api/companies/{assigned.id}",
        headers={**headers, "X-Company-Id": str(foreign.id)},
    )
    assert header_does_not_replace_the_path.status_code == 200
    assert header_does_not_replace_the_path.json()["id"] == str(assigned.id)

    denied = client.get(
        f"/api/companies/{foreign.id}",
        headers={**headers, "X-Company-Id": str(assigned.id)},
    )
    assert denied.status_code == 403
    assert "555-3333" not in denied.text


def test_unauthenticated_super_admin_route_stays_closed(client: TestClient, db: Session) -> None:
    company = make_company(db, name="Platform Company")
    response = client.get(f"/api/companies/{company.id}")
    assert response.status_code == 401
    assert "Platform Company" not in response.text


def test_authorize_company_query_count_stays_bounded(
    db: Session,
    engine: Engine,
) -> None:
    employee = make_user(db, email="bounded@example.com")
    company = make_company(db, name="Bounded Company")
    make_membership(db, employee, company, UserRole.EMPLOYEE)

    def check() -> None:
        authorize_company_access(db, employee, company.id)

    db.expire(company)
    statements = _select_statements(engine, check)
    assert len(statements) == 2, statements

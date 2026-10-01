"""Contacts, messages, company isolation, and bounded query counts."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import event, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.permissions import UserRole
from app.models.contact import Contact
from app.models.message import Message
from tests.conftest import auth_header, make_company, make_membership, make_user


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


def _contact(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {"first_name": "Ada", "last_name": "Lovelace"}
    body.update(overrides)
    return body


def test_contact_crud_search_filters_and_archive(client: TestClient, db: Session) -> None:
    owner = make_user(db, email="owner-crm@example.com", first_name="Olivia", last_name="Owner")
    employee = make_user(
        db,
        email="worker-crm@example.com",
        first_name="Evan",
        last_name="Employee",
    )
    company = make_company(db, name="Company A")
    make_membership(db, owner, company, UserRole.OWNER)
    make_membership(db, employee, company, UserRole.EMPLOYEE)
    headers = auth_header(owner)

    created = client.post(
        f"/api/companies/{company.id}/contacts",
        headers=headers,
        json=_contact(
            email="Ada@Example.com",
            phone="2145550100",
            company_name="Analytical Engines",
            source="referral",
            notes="Prefers morning calls",
            assigned_to_user_id=str(employee.id),
        ),
    )
    assert created.status_code == 201
    contact = created.json()
    assert contact["email"] == "ada@example.com"
    assert contact["assignee_name"] == "Evan Employee"
    assert contact["notes"] == "Prefers morning calls"
    contact_id = contact["id"]

    listed = client.get(f"/api/companies/{company.id}/contacts", headers=headers)
    assert listed.status_code == 200
    payload = listed.json()
    assert payload["page_size"] == 20
    assert payload["total"] == 1
    assert "notes" not in payload["items"][0]
    assert payload["items"][0]["assignee_name"] == "Evan Employee"

    searched = client.get(
        f"/api/companies/{company.id}/contacts",
        headers=headers,
        params={"search": "analytical", "source": "referral", "assigned_to": str(employee.id)},
    )
    assert searched.json()["total"] == 1
    missed = client.get(
        f"/api/companies/{company.id}/contacts",
        headers=headers,
        params={"search": "missing"},
    )
    assert missed.json()["total"] == 0

    updated = client.patch(
        f"/api/companies/{company.id}/contacts/{contact_id}",
        headers=headers,
        json={"status": "archived", "company_id": str(company.id)},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "archived"
    hidden = client.get(f"/api/companies/{company.id}/contacts", headers=headers)
    assert hidden.json()["total"] == 0
    archived = client.get(
        f"/api/companies/{company.id}/contacts",
        headers=headers,
        params={"status": "archived"},
    )
    assert archived.json()["total"] == 1

    detail = client.get(f"/api/companies/{company.id}/contacts/{contact_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["notes"] == "Prefers morning calls"


def test_duplicate_email_is_company_scoped(client: TestClient, db: Session) -> None:
    owner = make_user(db, email="owner-email@example.com")
    company_a = make_company(db, name="Email A")
    company_b = make_company(db, name="Email B")
    make_membership(db, owner, company_a, UserRole.OWNER)
    make_membership(db, owner, company_b, UserRole.OWNER)
    headers = auth_header(owner)
    first = client.post(
        f"/api/companies/{company_a.id}/contacts",
        headers=headers,
        json=_contact(email="shared@example.com", phone="2145550001"),
    )
    assert first.status_code == 201
    duplicate = client.post(
        f"/api/companies/{company_a.id}/contacts",
        headers=headers,
        json=_contact(first_name="Grace", email="SHARED@example.com", phone="2145550001"),
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["message"] == (
        "A contact with this email already exists in this company."
    )
    other_company = client.post(
        f"/api/companies/{company_b.id}/contacts",
        headers=headers,
        json=_contact(email="shared@example.com", phone="2145550001"),
    )
    assert other_company.status_code == 201
    blank_emails = [
        client.post(
            f"/api/companies/{company_a.id}/contacts",
            headers=headers,
            json=_contact(first_name=f"No{index}", last_name="Email"),
        )
        for index in range(2)
    ]
    assert [response.status_code for response in blank_emails] == [201, 201]


def test_contact_pagination_and_stable_order(client: TestClient, db: Session) -> None:
    owner = make_user(db, email="owner-pages@example.com")
    company = make_company(db, name="Paged Co")
    make_membership(db, owner, company, UserRole.OWNER)
    headers = auth_header(owner)
    for index in range(3):
        response = client.post(
            f"/api/companies/{company.id}/contacts",
            headers=headers,
            json=_contact(first_name=f"Person{index}", last_name="Page"),
        )
        assert response.status_code == 201
    stamp = datetime.now(UTC) - timedelta(days=1)
    for contact in db.scalars(select(Contact).where(Contact.company_id == company.id)):
        contact.created_at = stamp
    db.commit()
    page = client.get(
        f"/api/companies/{company.id}/contacts",
        headers=headers,
        params={"page": 1, "page_size": 2},
    )
    body = page.json()
    assert body["total"] == 3
    assert body["total_pages"] == 2
    assert len(body["items"]) == 2
    again = client.get(
        f"/api/companies/{company.id}/contacts",
        headers=headers,
        params={"page": 1, "page_size": 2},
    )
    assert [item["id"] for item in again.json()["items"]] == [item["id"] for item in body["items"]]
    assert client.get(
        f"/api/companies/{company.id}/contacts",
        headers=headers,
        params={"page": 0},
    ).status_code == 422
    assert client.get(
        f"/api/companies/{company.id}/contacts",
        headers=headers,
        params={"page_size": 0},
    ).status_code == 422
    assert client.get(
        f"/api/companies/{company.id}/contacts",
        headers=headers,
        params={"page_size": 101},
    ).status_code == 422


def test_contacts_are_isolated_and_assignment_stays_in_company(
    client: TestClient,
    db: Session,
) -> None:
    owner = make_user(db, email="owner-both@example.com", first_name="Olivia", last_name="Owner")
    employee_a = make_user(db, email="employee-a-crm@example.com")
    employee_b = make_user(db, email="employee-b-crm@example.com")
    company_a = make_company(db, name="Company A")
    company_b = make_company(db, name="Company B")
    company_c = make_company(db, name="Company C")
    make_membership(db, owner, company_a, UserRole.OWNER)
    make_membership(db, owner, company_b, UserRole.OWNER)
    make_membership(db, employee_a, company_a, UserRole.EMPLOYEE)
    make_membership(db, employee_b, company_b, UserRole.EMPLOYEE)
    headers = auth_header(owner)
    contact_a = client.post(
        f"/api/companies/{company_a.id}/contacts",
        headers=headers,
        json=_contact(email="private-a@example.com", assigned_to_user_id=str(employee_a.id)),
    )
    contact_b = client.post(
        f"/api/companies/{company_b.id}/contacts",
        headers=headers,
        json=_contact(first_name="Grace", email="private-b@example.com"),
    )
    assert contact_a.status_code == 201
    assert contact_b.status_code == 201
    only_a = client.get(f"/api/companies/{company_a.id}/contacts", headers=headers)
    assert [item["email"] for item in only_a.json()["items"]] == ["private-a@example.com"]
    only_b = client.get(f"/api/companies/{company_b.id}/contacts", headers=headers)
    assert [item["email"] for item in only_b.json()["items"]] == ["private-b@example.com"]

    leaked = client.get(
        f"/api/companies/{company_a.id}/contacts/{contact_b.json()['id']}",
        headers=headers,
    )
    assert leaked.status_code == 404
    assert "private-b@example.com" not in leaked.text
    assert "Company B" not in leaked.text

    denied = client.get(f"/api/companies/{company_c.id}/contacts", headers=headers)
    assert denied.status_code == 403

    cross_assign = client.post(
        f"/api/companies/{company_a.id}/contacts",
        headers=headers,
        json=_contact(first_name="Sam", assigned_to_user_id=str(employee_b.id)),
    )
    assert cross_assign.status_code == 400
    assert cross_assign.json()["error"]["message"] == "That person is not a member of this company."
    assert "Company B" not in cross_assign.text


def test_contact_role_matrix(client: TestClient, db: Session) -> None:
    company = make_company(db, name="Role Co")
    headers_by_role: dict[UserRole, dict[str, str]] = {}
    roles = (
        UserRole.OWNER,
        UserRole.COMPANY_MANAGER,
        UserRole.MARKETING_MANAGER,
        UserRole.EMPLOYEE,
    )
    for role in roles:
        user = make_user(db, email=f"{role.value}-crm@example.com")
        make_membership(db, user, company, role)
        headers_by_role[role] = auth_header(user)
    admin = make_user(db, email="root-crm@example.com", is_super_admin=True)

    denied = client.post(
        f"/api/companies/{company.id}/contacts",
        headers=headers_by_role[UserRole.EMPLOYEE],
        json=_contact(),
    )
    assert denied.status_code == 403
    for role in (UserRole.OWNER, UserRole.COMPANY_MANAGER, UserRole.MARKETING_MANAGER):
        created = client.post(
            f"/api/companies/{company.id}/contacts",
            headers=headers_by_role[role],
            json=_contact(first_name=role.value),
        )
        assert created.status_code == 201
    admin_created = client.post(
        f"/api/companies/{company.id}/contacts",
        headers=auth_header(admin),
        json=_contact(first_name="Root"),
    )
    assert admin_created.status_code == 201
    visible = client.get(
        f"/api/companies/{company.id}/contacts",
        headers=headers_by_role[UserRole.EMPLOYEE],
    )
    assert visible.status_code == 200
    assert visible.json()["total"] == 4


def test_contact_query_count_stays_bounded(
    client: TestClient,
    db: Session,
    engine: Engine,
) -> None:
    owner = make_user(
        db,
        email="owner-count-crm@example.com",
        first_name="Olivia",
        last_name="Owner",
    )
    company = make_company(db, name="Counted Contacts")
    make_membership(db, owner, company, UserRole.OWNER)
    headers = auth_header(owner)
    for index in range(50):
        db.add(
            Contact(
                company_id=company.id,
                first_name="Pat",
                last_name=f"{index:02d}",
                assigned_to_user_id=owner.id,
                source="manual",
                status="active",
            )
        )
    db.commit()

    def load(page_size: int) -> None:
        response = client.get(
            f"/api/companies/{company.id}/contacts",
            headers=headers,
            params={"page_size": page_size},
        )
        assert response.status_code == 200
        assert len(response.json()["items"]) == page_size

    counts = []
    for page_size in (10, 20, 50):
        db.expire_all()
        counts.append(len(_selects(engine, lambda size=page_size: load(size))))
    assert counts == [5, 5, 5]

    contact_id = db.scalar(select(Contact.id).where(Contact.company_id == company.id))
    assert contact_id is not None

    def load_detail() -> None:
        response = client.get(
            f"/api/companies/{company.id}/contacts/{contact_id}",
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["assignee_name"] == "Olivia Owner"

    db.expire_all()
    assert len(_selects(engine, load_detail)) == 4


def test_message_drafts_validation_and_history(client: TestClient, db: Session) -> None:
    employee = make_user(
        db,
        email="employee-msg@example.com",
        first_name="Evan",
        last_name="Employee",
    )
    writer = make_user(db, email="writer-msg@example.com")
    company = make_company(db, name="Message Co")
    make_membership(db, employee, company, UserRole.EMPLOYEE)
    make_membership(db, writer, company, UserRole.OWNER)
    headers = auth_header(employee)
    writer_headers = auth_header(writer)
    contact = client.post(
        f"/api/companies/{company.id}/contacts",
        headers=writer_headers,
        json=_contact(email="ada@example.com", phone="2145551212"),
    ).json()

    denied_empty = client.post(
        f"/api/companies/{company.id}/messages",
        headers=headers,
        json={"contact_id": contact["id"], "message_type": "email", "subject": "Hi", "body": "   "},
    )
    assert denied_empty.status_code == 422
    missing_subject = client.post(
        f"/api/companies/{company.id}/messages",
        headers=headers,
        json={"contact_id": contact["id"], "message_type": "email", "body": "Hello"},
    )
    assert missing_subject.status_code == 400
    missing_phone = client.post(
        f"/api/companies/{company.id}/contacts",
        headers=writer_headers,
        json=_contact(first_name="No", last_name="Phone", email="nophone@example.com"),
    )
    sms_denied = client.post(
        f"/api/companies/{company.id}/messages",
        headers=headers,
        json={
            "contact_id": missing_phone.json()["id"],
            "message_type": "sms",
            "body": "Hello",
        },
    )
    assert sms_denied.status_code == 400

    created = client.post(
        f"/api/companies/{company.id}/messages",
        headers=headers,
        json={
            "contact_id": contact["id"],
            "message_type": "email",
            "subject": "Welcome",
            "body": "Unique orchard offer",
            "deliver": True,
            "direction": "inbound",
            "status": "delivered",
        },
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["provider_status"] == "unavailable"
    assert payload["message"]["status"] == "draft"
    assert payload["message"]["direction"] == "outbound"
    assert payload["message"]["sent_at"] is None
    assert payload["message"]["error_message"] == "No email or SMS provider is configured."
    message_id = payload["message"]["id"]

    listed = client.get(
        f"/api/companies/{company.id}/messages",
        headers=headers,
        params={"search": "orchard", "message_type": "email", "status": "draft"},
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert "body" not in listed.json()["items"][0]
    assert listed.json()["items"][0]["contact_name"] == "Ada Lovelace"
    assert listed.json()["items"][0]["creator_name"] == "Evan Employee"

    edited = client.patch(
        f"/api/companies/{company.id}/messages/{message_id}",
        headers=headers,
        json={"body": "Updated draft"},
    )
    assert edited.status_code == 200
    assert edited.json()["body"] == "Updated draft"

    sms = client.post(
        f"/api/companies/{company.id}/messages",
        headers=headers,
        json={
            "contact_id": contact["id"],
            "message_type": "sms",
            "body": "Reminder",
            "deliver": False,
        },
    )
    assert sms.status_code == 201
    assert sms.json()["provider_status"] == "draft"
    assert sms.json()["message"]["subject"] is None
    assert sms.json()["message"]["status"] == "draft"


def test_messages_are_isolated(client: TestClient, db: Session) -> None:
    owner = make_user(db, email="owner-msg@example.com")
    company_a = make_company(db, name="Msg A")
    company_b = make_company(db, name="Msg B")
    company_c = make_company(db, name="Msg C")
    make_membership(db, owner, company_a, UserRole.OWNER)
    make_membership(db, owner, company_b, UserRole.OWNER)
    headers = auth_header(owner)
    contact_a = client.post(
        f"/api/companies/{company_a.id}/contacts",
        headers=headers,
        json=_contact(email="a@example.com", phone="2145551000"),
    ).json()
    contact_b = client.post(
        f"/api/companies/{company_b.id}/contacts",
        headers=headers,
        json=_contact(first_name="Bea", email="b@example.com", phone="2145552000"),
    ).json()
    message_b = client.post(
        f"/api/companies/{company_b.id}/messages",
        headers=headers,
        json={
            "contact_id": contact_b["id"],
            "message_type": "sms",
            "body": "Secret reminder",
        },
    )
    assert message_b.status_code == 201
    cross_contact = client.post(
        f"/api/companies/{company_a.id}/messages",
        headers=headers,
        json={
            "contact_id": contact_b["id"],
            "message_type": "email",
            "subject": "Hi",
            "body": "Nope",
        },
    )
    assert cross_contact.status_code == 404
    assert "b@example.com" not in cross_contact.text
    leaked = client.get(
        f"/api/companies/{company_a.id}/messages/{message_b.json()['message']['id']}",
        headers=headers,
    )
    assert leaked.status_code == 404
    assert "Secret reminder" not in leaked.text
    list_a = client.get(f"/api/companies/{company_a.id}/messages", headers=headers)
    list_b = client.get(f"/api/companies/{company_b.id}/messages", headers=headers)
    list_c = client.get(f"/api/companies/{company_c.id}/messages", headers=headers)
    assert list_a.json()["total"] == 0
    assert list_b.json()["total"] == 1
    assert list_c.status_code == 403
    own = client.post(
        f"/api/companies/{company_a.id}/messages",
        headers=headers,
        json={
            "contact_id": contact_a["id"],
            "message_type": "email",
            "subject": "Hello",
            "body": "Visible",
        },
    )
    assert own.status_code == 201


def test_message_query_count_stays_bounded(
    client: TestClient,
    db: Session,
    engine: Engine,
) -> None:
    owner = make_user(
        db,
        email="owner-msg-count@example.com",
        first_name="Olivia",
        last_name="Owner",
    )
    company = make_company(db, name="Counted Messages")
    make_membership(db, owner, company, UserRole.OWNER)
    contact = Contact(
        company_id=company.id,
        first_name="Ada",
        last_name="Lovelace",
        email="ada-count@example.com",
        source="manual",
        status="active",
    )
    db.add(contact)
    db.commit()
    for index in range(50):
        db.add(
            Message(
                company_id=company.id,
                contact_id=contact.id,
                created_by_user_id=owner.id,
                message_type="email",
                direction="outbound",
                subject=f"Note {index}",
                body="Bounded",
                status="draft",
            )
        )
    db.commit()
    headers = auth_header(owner)

    def load(page_size: int) -> None:
        response = client.get(
            f"/api/companies/{company.id}/messages",
            headers=headers,
            params={"page_size": page_size},
        )
        assert response.status_code == 200
        assert response.json()["items"][0]["contact_name"] == "Ada Lovelace"
        assert response.json()["items"][0]["creator_name"] == "Olivia Owner"

    counts = []
    for page_size in (10, 20, 50):
        db.expire_all()
        counts.append(len(_selects(engine, lambda size=page_size: load(size))))
    assert counts == [5, 5, 5]

    message_id = db.scalar(select(Message.id).where(Message.company_id == company.id))

    def load_detail() -> None:
        response = client.get(
            f"/api/companies/{company.id}/messages/{message_id}",
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["body"] == "Bounded"

    db.expire_all()
    assert len(_selects(engine, load_detail)) == 4


def test_only_drafts_can_be_edited(client: TestClient, db: Session) -> None:
    owner = make_user(db, email="owner-draft@example.com")
    company = make_company(db, name="Draft Co")
    make_membership(db, owner, company, UserRole.OWNER)
    contact = Contact(
        company_id=company.id,
        first_name="Ada",
        last_name="Lovelace",
        email="ada-draft@example.com",
        source="manual",
        status="active",
    )
    message = Message(
        company_id=company.id,
        contact_id=contact.id,
        created_by_user_id=owner.id,
        message_type="email",
        direction="outbound",
        subject="Sent already",
        body="Original",
        status="sent",
    )
    db.add(contact)
    db.add(message)
    db.commit()
    response = client.patch(
        f"/api/companies/{company.id}/messages/{message.id}",
        headers=auth_header(owner),
        json={"body": "Changed"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["message"] == "Only drafts can be edited."


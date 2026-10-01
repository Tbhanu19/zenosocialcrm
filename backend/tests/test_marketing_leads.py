"""Marketing campaigns, leads, isolation, and bounded query counts."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import event, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.permissions import UserRole
from app.models.campaign import MarketingCampaign
from app.models.contact import Contact
from app.models.lead import Lead
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


def _campaign(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "name": "Spring wash",
        "campaign_type": "promotion",
        "channel": "email",
    }
    body.update(overrides)
    return body


def _lead(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {"title": "Fleet inquiry", "source": "manual"}
    body.update(overrides)
    return body


def test_campaign_crud_search_filters_and_archive(client: TestClient, db: Session) -> None:
    owner = make_user(db, email="owner-mkt@example.com", first_name="Olivia", last_name="Owner")
    company = make_company(db, name="Company A")
    make_membership(db, owner, company, UserRole.OWNER)
    headers = auth_header(owner)

    created = client.post(
        f"/api/companies/{company.id}/marketing/campaigns",
        headers=headers,
        json=_campaign(
            description="Weekend special",
            status="active",
            start_date="2026-04-01",
            end_date="2026-04-30",
            budget="1500.50",
            source="newsletter",
            external_campaign_id="ext-100",
            notes="Internal only",
            company_id=str(company.id),
            created_by_user_id="00000000-0000-0000-0000-000000000000",
        ),
    )
    assert created.status_code == 201
    campaign = created.json()
    assert campaign["budget"] == "1500.50"
    assert campaign["created_by_user_id"] == str(owner.id)
    assert campaign["creator_name"] == "Olivia Owner"
    assert campaign["notes"] == "Internal only"
    assert "company_id" not in campaign
    campaign_id = campaign["id"]

    listed = client.get(f"/api/companies/{company.id}/marketing/campaigns", headers=headers)
    assert listed.status_code == 200
    payload = listed.json()
    assert payload["page_size"] == 20
    assert payload["total"] == 1
    assert "notes" not in payload["items"][0]
    assert "description" not in payload["items"][0]

    searched = client.get(
        f"/api/companies/{company.id}/marketing/campaigns",
        headers=headers,
        params={
            "search": "ext-100",
            "status": "active",
            "channel": "email",
            "campaign_type": "promotion",
            "start_date": "2026-04-01",
            "end_date": "2026-04-30",
        },
    )
    assert searched.json()["total"] == 1
    missed = client.get(
        f"/api/companies/{company.id}/marketing/campaigns",
        headers=headers,
        params={"search": "missing"},
    )
    assert missed.json()["total"] == 0

    paused = client.patch(
        f"/api/companies/{company.id}/marketing/campaigns/{campaign_id}",
        headers=headers,
        json={"status": "paused"},
    )
    assert paused.status_code == 200
    assert paused.json()["status"] == "paused"

    archived = client.patch(
        f"/api/companies/{company.id}/marketing/campaigns/{campaign_id}",
        headers=headers,
        json={"status": "archived"},
    )
    assert archived.status_code == 200
    hidden = client.get(f"/api/companies/{company.id}/marketing/campaigns", headers=headers)
    assert hidden.json()["total"] == 0
    shown = client.get(
        f"/api/companies/{company.id}/marketing/campaigns",
        headers=headers,
        params={"status": "archived"},
    )
    assert shown.json()["total"] == 1

    detail = client.get(
        f"/api/companies/{company.id}/marketing/campaigns/{campaign_id}",
        headers=headers,
    )
    assert detail.status_code == 200
    assert detail.json()["external_campaign_id"] == "ext-100"


def test_campaign_dates_and_budget(client: TestClient, db: Session) -> None:
    owner = make_user(db, email="owner-mkt-valid@example.com")
    company = make_company(db, name="Valid Co")
    make_membership(db, owner, company, UserRole.OWNER)
    headers = auth_header(owner)
    negative = client.post(
        f"/api/companies/{company.id}/marketing/campaigns",
        headers=headers,
        json=_campaign(budget="-1"),
    )
    assert negative.status_code == 422
    dates = client.post(
        f"/api/companies/{company.id}/marketing/campaigns",
        headers=headers,
        json=_campaign(start_date="2026-05-02", end_date="2026-05-01"),
    )
    assert dates.status_code == 422
    created = client.post(
        f"/api/companies/{company.id}/marketing/campaigns",
        headers=headers,
        json=_campaign(status="active", start_date="2020-01-01", end_date="2020-01-02"),
    )
    assert created.status_code == 201
    assert created.json()["status"] == "active"
    crossed = client.patch(
        f"/api/companies/{company.id}/marketing/campaigns/{created.json()['id']}",
        headers=headers,
        json={"start_date": "2026-06-10"},
    )
    assert crossed.status_code == 400
    assert crossed.json()["error"]["message"] == "End date must be on or after the start date."
    empty = client.patch(
        f"/api/companies/{company.id}/marketing/campaigns/{created.json()['id']}",
        headers=headers,
        json={},
    )
    assert empty.status_code == 400


def test_campaign_pagination(client: TestClient, db: Session) -> None:
    owner = make_user(db, email="owner-mkt-pages@example.com")
    company = make_company(db, name="Paged Campaigns")
    make_membership(db, owner, company, UserRole.OWNER)
    headers = auth_header(owner)
    for index in range(3):
        response = client.post(
            f"/api/companies/{company.id}/marketing/campaigns",
            headers=headers,
            json=_campaign(name=f"Campaign {index}"),
        )
        assert response.status_code == 201
    stamp = datetime.now(UTC) - timedelta(days=1)
    for campaign in db.scalars(
        select(MarketingCampaign).where(MarketingCampaign.company_id == company.id)
    ):
        campaign.created_at = stamp
    db.commit()
    page = client.get(
        f"/api/companies/{company.id}/marketing/campaigns",
        headers=headers,
        params={"page": 1, "page_size": 2},
    )
    body = page.json()
    assert body["total"] == 3
    assert body["total_pages"] == 2
    assert len(body["items"]) == 2
    again = client.get(
        f"/api/companies/{company.id}/marketing/campaigns",
        headers=headers,
        params={"page": 1, "page_size": 2},
    )
    assert [item["id"] for item in again.json()["items"]] == [item["id"] for item in body["items"]]
    assert client.get(
        f"/api/companies/{company.id}/marketing/campaigns",
        headers=headers,
        params={"page": 0},
    ).status_code == 422
    assert client.get(
        f"/api/companies/{company.id}/marketing/campaigns",
        headers=headers,
        params={"page_size": 101},
    ).status_code == 422


def test_lead_crud_search_filters_and_relationships(client: TestClient, db: Session) -> None:
    owner = make_user(db, email="owner-lead@example.com", first_name="Olivia", last_name="Owner")
    outsider = make_user(db, email="outsider-lead@example.com", first_name="Out", last_name="Sider")
    company = make_company(db, name="Lead A")
    other = make_company(db, name="Lead B")
    make_membership(db, owner, company, UserRole.OWNER)
    make_membership(db, outsider, other, UserRole.OWNER)
    headers = auth_header(owner)
    contact = Contact(
        company_id=company.id,
        first_name="John",
        last_name="Smith",
        email="john@example.com",
        phone="555-0100",
        source="manual",
        status="active",
    )
    foreign_contact = Contact(
        company_id=other.id,
        first_name="Secret",
        last_name="Person",
        email="secret@example.com",
        phone="555-0199",
        source="manual",
        status="active",
    )
    db.add_all([contact, foreign_contact])
    db.commit()
    campaign = client.post(
        f"/api/companies/{company.id}/marketing/campaigns",
        headers=headers,
        json=_campaign(name="Google spring", channel="google", status="active"),
    )
    assert campaign.status_code == 201
    campaign_id = campaign.json()["id"]
    foreign_campaign = MarketingCampaign(
        company_id=other.id,
        name="Secret campaign",
        campaign_type="social",
        channel="facebook",
        status="active",
        created_by_user_id=outsider.id,
    )
    db.add(foreign_campaign)
    db.commit()

    created = client.post(
        f"/api/companies/{company.id}/leads",
        headers=headers,
        json=_lead(
            title="John fleet",
            description="Needs ten washes",
            contact_id=str(contact.id),
            campaign_id=campaign_id,
            source="google",
            priority="high",
            assigned_to_user_id=str(owner.id),
            estimated_value="2500.00",
            expected_close_date="2026-07-01",
            notes="Call Friday",
            company_id=str(other.id),
        ),
    )
    assert created.status_code == 201
    lead = created.json()
    assert lead["contact_name"] == "John Smith"
    assert lead["campaign_name"] == "Google spring"
    assert lead["campaign_status"] == "active"
    assert lead["assignee_name"] == "Olivia Owner"
    assert lead["estimated_value"] == "2500.00"
    assert lead["email"] is None
    assert "company_id" not in lead
    lead_id = lead["id"]

    listed = client.get(f"/api/companies/{company.id}/leads", headers=headers)
    assert listed.json()["total"] == 1
    assert "notes" not in listed.json()["items"][0]
    searched = client.get(
        f"/api/companies/{company.id}/leads",
        headers=headers,
        params={
            "search": "john@example.com",
            "status": "new",
            "source": "google",
            "priority": "high",
            "campaign_id": campaign_id,
            "assigned_to": str(owner.id),
        },
    )
    assert searched.json()["total"] == 1
    by_phone = client.get(
        f"/api/companies/{company.id}/leads",
        headers=headers,
        params={"search": "555-0100"},
    )
    assert by_phone.json()["total"] == 1

    qualified = client.patch(
        f"/api/companies/{company.id}/leads/{lead_id}",
        headers=headers,
        json={"status": "qualified", "priority": "low"},
    )
    assert qualified.status_code == 200
    assert qualified.json()["status"] == "qualified"
    assert qualified.json()["priority"] == "low"

    bad_contact = client.post(
        f"/api/companies/{company.id}/leads",
        headers=headers,
        json=_lead(contact_id=str(foreign_contact.id)),
    )
    assert bad_contact.status_code == 404
    assert bad_contact.json()["error"]["message"] == "Contact not found."
    assert "secret@example.com" not in bad_contact.text
    bad_campaign = client.post(
        f"/api/companies/{company.id}/leads",
        headers=headers,
        json=_lead(campaign_id=str(foreign_campaign.id)),
    )
    assert bad_campaign.status_code == 404
    assert bad_campaign.json()["error"]["message"] == "Campaign not found."
    assert "Secret campaign" not in bad_campaign.text
    bad_user = client.post(
        f"/api/companies/{company.id}/leads",
        headers=headers,
        json=_lead(assigned_to_user_id=str(outsider.id)),
    )
    assert bad_user.status_code == 400
    assert bad_user.json()["error"]["message"] == "That person is not a member of this company."
    negative = client.post(
        f"/api/companies/{company.id}/leads",
        headers=headers,
        json=_lead(estimated_value="-5"),
    )
    assert negative.status_code == 422
    archived_create = client.post(
        f"/api/companies/{company.id}/leads",
        headers=headers,
        json=_lead(status="archived"),
    )
    assert archived_create.status_code == 422

    archived = client.patch(
        f"/api/companies/{company.id}/leads/{lead_id}",
        headers=headers,
        json={"status": "archived"},
    )
    assert archived.status_code == 200
    hidden = client.get(f"/api/companies/{company.id}/leads", headers=headers)
    assert hidden.json()["total"] == 0


def test_company_isolation_and_roles(client: TestClient, db: Session) -> None:
    owner = make_user(db, email="owner-iso-mkt@example.com")
    manager = make_user(db, email="mgr-iso-mkt@example.com")
    marketer = make_user(db, email="mkt-iso@example.com")
    employee = make_user(db, email="emp-iso-mkt@example.com")
    super_admin = make_user(db, email="root-mkt@example.com", is_super_admin=True)
    company_a = make_company(db, name="Iso A")
    company_b = make_company(db, name="Iso B")
    company_c = make_company(db, name="Iso C")
    make_membership(db, owner, company_a, UserRole.OWNER)
    make_membership(db, owner, company_b, UserRole.OWNER)
    make_membership(db, manager, company_a, UserRole.COMPANY_MANAGER)
    make_membership(db, marketer, company_a, UserRole.MARKETING_MANAGER)
    make_membership(db, employee, company_a, UserRole.EMPLOYEE)
    owner_headers = auth_header(owner)
    created = client.post(
        f"/api/companies/{company_a.id}/marketing/campaigns",
        headers=owner_headers,
        json=_campaign(name="Company A only"),
    )
    assert created.status_code == 201
    campaign_id = created.json()["id"]
    lead = client.post(
        f"/api/companies/{company_a.id}/leads",
        headers=owner_headers,
        json=_lead(title="Company A lead", campaign_id=campaign_id),
    )
    assert lead.status_code == 201
    lead_id = lead.json()["id"]

    for path in (
        f"/api/companies/{company_b.id}/marketing/campaigns/{campaign_id}",
        f"/api/companies/{company_b.id}/leads/{lead_id}",
        f"/api/companies/{company_b.id}/marketing/campaigns/{campaign_id}/leads",
    ):
        response = client.get(path, headers=owner_headers)
        assert response.status_code == 404
        assert "Company A only" not in response.text
        assert "Company A lead" not in response.text

    denied = client.get(
        f"/api/companies/{company_c.id}/marketing/campaigns",
        headers=owner_headers,
    )
    assert denied.status_code == 403
    denied_leads = client.get(f"/api/companies/{company_c.id}/leads", headers=owner_headers)
    assert denied_leads.status_code == 403

    company_b_list = client.get(
        f"/api/companies/{company_b.id}/marketing/campaigns",
        headers=owner_headers,
    )
    assert company_b_list.json()["total"] == 0
    company_b_leads = client.get(f"/api/companies/{company_b.id}/leads", headers=owner_headers)
    assert company_b_leads.json()["total"] == 0

    employee_headers = auth_header(employee)
    assert client.get(
        f"/api/companies/{company_a.id}/marketing/campaigns",
        headers=employee_headers,
    ).status_code == 403
    assert client.post(
        f"/api/companies/{company_a.id}/leads",
        headers=employee_headers,
        json=_lead(),
    ).status_code == 403

    for actor in (manager, marketer, super_admin):
        response = client.post(
            f"/api/companies/{company_a.id}/leads",
            headers=auth_header(actor),
            json=_lead(title=f"From {actor.email}"),
        )
        assert response.status_code == 201


def test_campaign_leads_are_paginated_and_scoped(client: TestClient, db: Session) -> None:
    owner = make_user(db, email="owner-attr@example.com")
    company = make_company(db, name="Attribution")
    other = make_company(db, name="Other Attribution")
    make_membership(db, owner, company, UserRole.OWNER)
    headers = auth_header(owner)
    campaign = client.post(
        f"/api/companies/{company.id}/marketing/campaigns",
        headers=headers,
        json=_campaign(name="Attributed", status="active"),
    )
    campaign_id = campaign.json()["id"]
    other_campaign = client.post(
        f"/api/companies/{company.id}/marketing/campaigns",
        headers=headers,
        json=_campaign(name="Unrelated"),
    )
    for index in range(3):
        created = client.post(
            f"/api/companies/{company.id}/leads",
            headers=headers,
            json=_lead(title=f"Attributed {index}", campaign_id=campaign_id, source="campaign"),
        )
        assert created.status_code == 201
    extra = client.post(
        f"/api/companies/{company.id}/leads",
        headers=headers,
        json=_lead(title="Somewhere else", campaign_id=other_campaign.json()["id"]),
    )
    assert extra.status_code == 201
    page = client.get(
        f"/api/companies/{company.id}/marketing/campaigns/{campaign_id}/leads",
        headers=headers,
        params={"page_size": 2},
    )
    assert page.status_code == 200
    assert page.json()["total"] == 3
    assert len(page.json()["items"]) == 2
    assert all(item["campaign_id"] == campaign_id for item in page.json()["items"])
    foreign = MarketingCampaign(
        company_id=other.id,
        name="Hidden campaign",
        campaign_type="other",
        channel="direct",
        status="active",
    )
    db.add(foreign)
    db.commit()
    missing = client.get(
        f"/api/companies/{company.id}/marketing/campaigns/{foreign.id}/leads",
        headers=headers,
    )
    assert missing.status_code == 404
    assert "Hidden campaign" not in missing.text


def test_marketing_summary_uses_aggregates(client: TestClient, db: Session) -> None:
    owner = make_user(db, email="owner-summary@example.com")
    company = make_company(db, name="Summary Co")
    make_membership(db, owner, company, UserRole.OWNER)
    headers = auth_header(owner)
    active = client.post(
        f"/api/companies/{company.id}/marketing/campaigns",
        headers=headers,
        json=_campaign(status="active"),
    )
    draft = client.post(
        f"/api/companies/{company.id}/marketing/campaigns",
        headers=headers,
        json=_campaign(name="Draft only"),
    )
    assert active.status_code == 201
    assert draft.status_code == 201
    for status in ("new", "new", "converted", "archived"):
        created = client.post(
            f"/api/companies/{company.id}/leads",
            headers=headers,
            json=_lead(title=status, status="new" if status == "archived" else status),
        )
        assert created.status_code == 201
        if status == "archived":
            archived = client.patch(
                f"/api/companies/{company.id}/leads/{created.json()['id']}",
                headers=headers,
                json={"status": "archived"},
            )
            assert archived.status_code == 200
    summary = client.get(f"/api/companies/{company.id}/marketing/summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json() == {
        "active_campaigns": 1,
        "total_leads": 3,
        "new_leads": 2,
        "converted_leads": 1,
    }


def test_lead_date_filter_and_pagination(client: TestClient, db: Session) -> None:
    owner = make_user(db, email="owner-lead-pages@example.com")
    company = make_company(db, name="Lead Pages")
    make_membership(db, owner, company, UserRole.OWNER)
    headers = auth_header(owner)
    for index in range(3):
        response = client.post(
            f"/api/companies/{company.id}/leads",
            headers=headers,
            json=_lead(title=f"Lead {index}"),
        )
        assert response.status_code == 201
    stamp = datetime(2026, 3, 15, tzinfo=UTC)
    for lead in db.scalars(select(Lead).where(Lead.company_id == company.id)):
        lead.created_at = stamp
    db.commit()
    window = client.get(
        f"/api/companies/{company.id}/leads",
        headers=headers,
        params={"created_from": "2026-03-15", "created_to": "2026-03-15"},
    )
    assert window.json()["total"] == 3
    outside = client.get(
        f"/api/companies/{company.id}/leads",
        headers=headers,
        params={"created_from": "2026-03-16"},
    )
    assert outside.json()["total"] == 0
    page = client.get(
        f"/api/companies/{company.id}/leads",
        headers=headers,
        params={"page": 1, "page_size": 2},
    )
    assert page.json()["total"] == 3
    assert len(page.json()["items"]) == 2
    assert client.get(
        f"/api/companies/{company.id}/leads",
        headers=headers,
        params={"page_size": 0},
    ).status_code == 422


def test_query_counts_stay_bounded(
    client: TestClient,
    db: Session,
    engine: Engine,
) -> None:
    owner = make_user(
        db,
        email="owner-mkt-count@example.com",
        first_name="Olivia",
        last_name="Owner",
    )
    company = make_company(db, name="Counted Marketing")
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
    campaign = MarketingCampaign(
        company_id=company.id,
        name="Counted",
        campaign_type="email",
        channel="email",
        status="active",
        budget=Decimal("10.00"),
        created_by_user_id=owner.id,
    )
    db.add(campaign)
    db.commit()
    for index in range(100):
        db.add(
            MarketingCampaign(
                company_id=company.id,
                name=f"Campaign {index:03d}",
                campaign_type="social",
                channel="instagram",
                status="draft",
                created_by_user_id=owner.id,
            )
        )
        db.add(
            Lead(
                company_id=company.id,
                contact_id=contact.id,
                campaign_id=campaign.id,
                title=f"Lead {index:03d}",
                status="new",
                source="campaign",
                priority="medium",
                assigned_to_user_id=owner.id,
                estimated_value=Decimal("20.00"),
            )
        )
    db.commit()
    headers = auth_header(owner)
    company_url = str(company.id)
    campaign_url = str(campaign.id)
    lead_id = db.scalar(select(Lead.id).where(Lead.company_id == company.id))
    assert lead_id is not None

    def campaigns(page_size: int) -> None:
        response = client.get(
            f"/api/companies/{company_url}/marketing/campaigns",
            headers=headers,
            params={"page_size": page_size},
        )
        assert response.status_code == 200
        assert len(response.json()["items"]) == page_size

    def campaign_detail() -> None:
        response = client.get(
            f"/api/companies/{company_url}/marketing/campaigns/{campaign_url}",
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["creator_name"] == "Olivia Owner"

    def leads(page_size: int) -> None:
        response = client.get(
            f"/api/companies/{company_url}/leads",
            headers=headers,
            params={"page_size": page_size},
        )
        assert response.status_code == 200
        assert len(response.json()["items"]) == page_size
        assert response.json()["items"][0]["contact_name"] == "Ada Lovelace"
        assert response.json()["items"][0]["campaign_name"] == "Counted"

    def lead_detail() -> None:
        response = client.get(
            f"/api/companies/{company_url}/leads/{lead_id}",
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["assignee_name"] == "Olivia Owner"

    def campaign_leads(page_size: int) -> None:
        response = client.get(
            f"/api/companies/{company_url}/marketing/campaigns/{campaign_url}/leads",
            headers=headers,
            params={"page_size": page_size},
        )
        assert response.status_code == 200
        assert len(response.json()["items"]) == page_size

    campaign_counts = []
    lead_counts = []
    campaign_lead_counts = []
    for page_size in (10, 20, 50, 100):
        db.expire_all()
        campaign_counts.append(len(_selects(engine, lambda size=page_size: campaigns(size))))
        db.expire_all()
        lead_counts.append(len(_selects(engine, lambda size=page_size: leads(size))))
        db.expire_all()
        campaign_lead_counts.append(
            len(_selects(engine, lambda size=page_size: campaign_leads(size)))
        )
    db.expire_all()
    detail_count = len(_selects(engine, campaign_detail))
    db.expire_all()
    lead_detail_count = len(_selects(engine, lead_detail))
    assert campaign_counts == [5, 5, 5, 5]
    assert lead_counts == [5, 5, 5, 5]
    assert campaign_lead_counts == [6, 6, 6, 6]
    assert detail_count == 4
    assert lead_detail_count == 4

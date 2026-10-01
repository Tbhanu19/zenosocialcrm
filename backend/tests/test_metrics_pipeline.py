"""Lead metrics, sales pipelines, isolation, and bounded queries."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

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


def _lead(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {"title": "Inquiry", "source": "manual"}
    body.update(overrides)
    return body


def test_lead_metrics_definitions_and_filters(client: TestClient, db: Session) -> None:
    owner = make_user(db, email="owner-metrics@example.com")
    other = make_user(db, email="other-metrics@example.com")
    company = make_company(db, name="Metrics A")
    elsewhere = make_company(db, name="Metrics B")
    make_membership(db, owner, company, UserRole.OWNER)
    make_membership(db, other, elsewhere, UserRole.OWNER)
    headers = auth_header(owner)
    campaign = MarketingCampaign(
        company_id=company.id,
        name="Spring wash",
        campaign_type="promotion",
        channel="email",
        status="active",
        created_by_user_id=owner.id,
    )
    hidden = MarketingCampaign(
        company_id=elsewhere.id,
        name="Secret campaign",
        campaign_type="social",
        channel="facebook",
        status="active",
    )
    db.add_all([campaign, hidden])
    db.commit()
    specs = [
        ("new", "website", None),
        ("contacted", "google", campaign.id),
        ("qualified", "website", campaign.id),
        ("unqualified", "manual", None),
        ("converted", "website", campaign.id),
        ("lost", "referral", None),
        ("archived", "website", campaign.id),
    ]
    for status, source, campaign_id in specs:
        db.add(
            Lead(
                company_id=company.id,
                title=f"{status} lead",
                status=status,
                source=source,
                priority="medium",
                campaign_id=campaign_id,
                assigned_to_user_id=owner.id if status == "converted" else None,
                estimated_value=Decimal("10.00"),
            )
        )
    db.add(
        Lead(
            company_id=elsewhere.id,
            title="Secret lead",
            status="converted",
            source="facebook",
            priority="high",
            campaign_id=hidden.id,
        )
    )
    db.commit()

    metrics = client.get(f"/api/companies/{company.id}/lead-metrics", headers=headers)
    assert metrics.status_code == 200
    body = metrics.json()
    assert body["summary"] == {
        "total_leads": 6,
        "new_leads": 1,
        "contacted_leads": 1,
        "qualified_leads": 1,
        "unqualified_leads": 1,
        "converted_leads": 1,
        "lost_leads": 1,
        "conversion_rate": "16.67",
    }
    assert {item["status"]: item["count"] for item in body["by_status"]}["converted"] == 1
    sources = {item["source"]: item["count"] for item in body["by_source"]}
    assert sources["website"] == 3
    assert "facebook" not in sources
    campaigns = {item["campaign_name"]: item for item in body["by_campaign"]}
    assert campaigns["Spring wash"]["lead_count"] == 3
    assert campaigns["Spring wash"]["converted_count"] == 1
    assert "Secret campaign" not in campaigns
    assert body["interval"] == "month"
    assert all("title" not in item for item in body["by_campaign"])

    website = client.get(
        f"/api/companies/{company.id}/lead-metrics",
        headers=headers,
        params={"source": "website", "campaign_id": str(campaign.id)},
    )
    assert website.json()["summary"]["total_leads"] == 2
    assigned = client.get(
        f"/api/companies/{company.id}/lead-metrics",
        headers=headers,
        params={"assigned_to_user_id": str(owner.id), "status": "converted"},
    )
    assert assigned.json()["summary"]["total_leads"] == 1
    assert assigned.json()["summary"]["conversion_rate"] == "100.00"
    empty = client.get(
        f"/api/companies/{company.id}/lead-metrics",
        headers=headers,
        params={"date_from": "2099-01-01", "date_to": "2099-01-02"},
    )
    assert empty.json()["summary"]["total_leads"] == 0
    assert empty.json()["summary"]["conversion_rate"] == "0.00"
    assert empty.json()["interval"] == "day"
    assert empty.json()["over_time"] == []
    assert "Secret lead" not in empty.text

    denied = client.get(f"/api/companies/{elsewhere.id}/lead-metrics", headers=headers)
    assert denied.status_code == 403


def test_metrics_roles_and_query_count(
    client: TestClient,
    db: Session,
    engine: Engine,
) -> None:
    owner = make_user(db, email="owner-metric-count@example.com")
    marketer = make_user(db, email="marketer-metrics@example.com")
    employee = make_user(db, email="employee-metrics@example.com")
    admin = make_user(db, email="root-metrics@example.com", is_super_admin=True)
    company = make_company(db, name="Counted Metrics")
    make_membership(db, owner, company, UserRole.OWNER)
    make_membership(db, marketer, company, UserRole.MARKETING_MANAGER)
    make_membership(db, employee, company, UserRole.EMPLOYEE)
    for index in range(40):
        db.add(
            Lead(
                company_id=company.id,
                title=f"Lead {index}",
                status="new" if index % 2 == 0 else "converted",
                source="manual",
                priority="medium",
            )
        )
    db.commit()
    headers = auth_header(owner)
    path = f"/api/companies/{company.id}/lead-metrics"

    def load() -> None:
        response = client.get(path, headers=headers)
        assert response.status_code == 200
        assert response.json()["summary"]["total_leads"] == 40
        assert "items" not in response.json()

    db.expire_all()
    first = len(_selects(engine, load))
    for index in range(40):
        db.add(
            Lead(
                company_id=company.id,
                title=f"More {index}",
                status="qualified",
                source="google",
                priority="low",
            )
        )
    db.commit()

    def load_more() -> None:
        response = client.get(path, headers=headers)
        assert response.status_code == 200
        assert response.json()["summary"]["total_leads"] == 80

    db.expire_all()
    second = len(_selects(engine, load_more))
    assert first == second
    assert first <= 8
    assert client.get(path, headers=auth_header(marketer)).status_code == 200
    assert client.get(path, headers=auth_header(employee)).status_code == 403
    assert client.get(path, headers=auth_header(admin)).status_code == 200


def test_pipeline_stages_movement_and_isolation(client: TestClient, db: Session) -> None:
    owner = make_user(db, email="owner-pipe@example.com", first_name="Olivia", last_name="Owner")
    manager = make_user(db, email="manager-pipe@example.com")
    marketer = make_user(db, email="marketer-pipe@example.com")
    employee = make_user(db, email="employee-pipe@example.com")
    company_a = make_company(db, name="Pipe A")
    company_b = make_company(db, name="Pipe B")
    company_c = make_company(db, name="Pipe C")
    make_membership(db, owner, company_a, UserRole.OWNER)
    make_membership(db, owner, company_b, UserRole.OWNER)
    make_membership(db, manager, company_a, UserRole.COMPANY_MANAGER)
    make_membership(db, marketer, company_a, UserRole.MARKETING_MANAGER)
    make_membership(db, employee, company_a, UserRole.EMPLOYEE)
    headers = auth_header(owner)
    contact = Contact(
        company_id=company_a.id,
        first_name="John",
        last_name="Smith",
        email="john-pipe@example.com",
        source="manual",
        status="active",
    )
    db.add(contact)
    db.commit()

    denied_config = client.post(
        f"/api/companies/{company_a.id}/sales-pipelines",
        headers=auth_header(marketer),
        json={"name": "Not allowed", "company_id": str(company_b.id)},
    )
    assert denied_config.status_code == 403
    assert client.post(
        f"/api/companies/{company_a.id}/sales-pipelines",
        headers=auth_header(employee),
        json={"name": "No"},
    ).status_code == 403

    created = client.post(
        f"/api/companies/{company_a.id}/sales-pipelines",
        headers=headers,
        json={"name": "Default sales", "description": "Main", "company_id": str(company_b.id)},
    )
    assert created.status_code == 201
    pipeline_id = created.json()["id"]
    assert created.json()["stages"] == []
    assert "company_id" not in created.json()

    stage_ids = []
    for name in ("New", "Qualified", "Won"):
        stage = client.post(
            f"/api/companies/{company_a.id}/sales-pipelines/{pipeline_id}/stages",
            headers=auth_header(manager),
            json={"name": name, "color": "pine"},
        )
        assert stage.status_code == 201
        stage_ids.append(stage.json()["id"])
    reordered = client.patch(
        f"/api/companies/{company_a.id}/sales-pipelines/{pipeline_id}/stages/reorder",
        headers=headers,
        json={"stage_ids": [stage_ids[1], stage_ids[0], stage_ids[2]]},
    )
    assert reordered.status_code == 200
    assert [item["name"] for item in reordered.json()] == ["Qualified", "New", "Won"]
    assert [item["position"] for item in reordered.json()] == [1, 2, 3]
    incomplete = client.patch(
        f"/api/companies/{company_a.id}/sales-pipelines/{pipeline_id}/stages/reorder",
        headers=headers,
        json={"stage_ids": [stage_ids[0]]},
    )
    assert incomplete.status_code == 400

    lead = client.post(
        f"/api/companies/{company_a.id}/leads",
        headers=headers,
        json=_lead(
            title="Fleet deal",
            contact_id=str(contact.id),
            estimated_value="2500.00",
            assigned_to_user_id=str(owner.id),
            expected_close_date="2026-10-01",
        ),
    )
    assert lead.status_code == 201
    lead_id = lead.json()["id"]
    assert lead.json()["status"] == "new"
    moved = client.patch(
        f"/api/companies/{company_a.id}/leads/{lead_id}/pipeline",
        headers=auth_header(marketer),
        json={
            "pipeline_id": pipeline_id,
            "pipeline_stage_id": stage_ids[2],
            "expected_pipeline_stage_id": None,
        },
    )
    assert moved.status_code == 200
    assert moved.json()["status"] == "new"
    assert moved.json()["stage_name"] == "Won"
    stale = client.patch(
        f"/api/companies/{company_a.id}/leads/{lead_id}/pipeline",
        headers=headers,
        json={
            "pipeline_id": pipeline_id,
            "pipeline_stage_id": stage_ids[0],
            "expected_pipeline_stage_id": None,
        },
    )
    assert stale.status_code == 409

    other = client.post(
        f"/api/companies/{company_b.id}/sales-pipelines",
        headers=headers,
        json={"name": "Company B pipeline"},
    )
    other_id = other.json()["id"]
    other_stage = client.post(
        f"/api/companies/{company_b.id}/sales-pipelines/{other_id}/stages",
        headers=headers,
        json={"name": "Hidden"},
    )
    cross = client.patch(
        f"/api/companies/{company_a.id}/leads/{lead_id}/pipeline",
        headers=headers,
        json={
            "pipeline_id": other_id,
            "pipeline_stage_id": other_stage.json()["id"],
            "expected_pipeline_stage_id": stage_ids[2],
        },
    )
    assert cross.status_code == 404
    assert "Hidden" not in cross.text
    assert client.get(
        f"/api/companies/{company_b.id}/sales-pipelines/{pipeline_id}",
        headers=headers,
    ).status_code == 404
    assert client.get(
        f"/api/companies/{company_c.id}/sales-pipelines",
        headers=headers,
    ).status_code == 403

    blocked = client.patch(
        f"/api/companies/{company_a.id}/sales-pipelines/{pipeline_id}/stages/{stage_ids[2]}",
        headers=headers,
        json={"status": "inactive"},
    )
    assert blocked.status_code == 409
    client.patch(
        f"/api/companies/{company_a.id}/leads/{lead_id}/pipeline",
        headers=headers,
        json={
            "pipeline_id": pipeline_id,
            "pipeline_stage_id": stage_ids[0],
            "expected_pipeline_stage_id": stage_ids[2],
        },
    )
    cleared = client.patch(
        f"/api/companies/{company_a.id}/sales-pipelines/{pipeline_id}/stages/{stage_ids[2]}",
        headers=headers,
        json={"status": "inactive"},
    )
    assert cleared.status_code == 200

    board = client.get(
        f"/api/companies/{company_a.id}/sales-pipelines/{pipeline_id}/board",
        headers=headers,
    )
    assert board.status_code == 200
    columns = {item["stage_name"]: item for item in board.json()["stages"]}
    assert "Won" not in columns
    assert columns["New"]["lead_count"] == 1
    assert columns["New"]["estimated_value_total"] == "2500.00"
    card = columns["New"]["leads"][0]
    assert card["title"] == "Fleet deal"
    assert card["contact_name"] == "John Smith"
    assert card["assignee_name"] == "Olivia Owner"
    assert "notes" not in card
    assert "description" not in card


def test_pipeline_board_query_count_stays_bounded(
    client: TestClient,
    db: Session,
    engine: Engine,
) -> None:
    owner = make_user(
        db,
        email="owner-board-count@example.com",
        first_name="Olivia",
        last_name="Owner",
    )
    company = make_company(db, name="Board Co")
    make_membership(db, owner, company, UserRole.OWNER)
    pipeline = client.post(
        f"/api/companies/{company.id}/sales-pipelines",
        headers=auth_header(owner),
        json={"name": "Board"},
    ).json()
    stages = []
    for index in range(7):
        stage = client.post(
            f"/api/companies/{company.id}/sales-pipelines/{pipeline['id']}/stages",
            headers=auth_header(owner),
            json={"name": f"Stage {index}"},
        )
        assert stage.status_code == 201
        stages.append(stage.json()["id"])
    contact = Contact(
        company_id=company.id,
        first_name="Ada",
        last_name="Lovelace",
        email="ada-board@example.com",
        source="manual",
        status="active",
    )
    db.add(contact)
    db.commit()

    pipeline_id = UUID(pipeline["id"])

    def add_leads(per_stage: int) -> None:
        for stage_id in stages:
            stage_uuid = UUID(stage_id)
            have = len(
                db.scalars(select(Lead.id).where(Lead.pipeline_stage_id == stage_uuid)).all()
            )
            for index in range(have, per_stage):
                db.add(
                    Lead(
                        company_id=company.id,
                        contact_id=contact.id,
                        title=f"{stage_id}-{index}",
                        status="new",
                        source="manual",
                        priority="medium",
                        assigned_to_user_id=owner.id,
                        estimated_value=Decimal("5.00"),
                        pipeline_id=pipeline_id,
                        pipeline_stage_id=stage_uuid,
                        created_at=datetime.now(UTC) - timedelta(minutes=index),
                    )
                )
        db.commit()

    headers = auth_header(owner)
    company_url = str(company.id)
    pipeline_url = str(pipeline["id"])

    def load(per_stage: int) -> None:
        response = client.get(
            f"/api/companies/{company_url}/sales-pipelines/{pipeline_url}/board",
            headers=headers,
            params={"per_stage": per_stage},
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body["stages"]) == 7
        assert body["stages"][0]["lead_count"] >= per_stage
        assert len(body["stages"][0]["leads"]) <= per_stage
        if body["stages"][0]["lead_count"] > per_stage:
            assert body["stages"][0]["has_more"] is True
            assert len(body["stages"][0]["leads"]) == per_stage

    add_leads(20)
    db.expire_all()
    first = len(_selects(engine, lambda: load(20)))
    add_leads(40)
    db.expire_all()
    second = len(_selects(engine, lambda: load(20)))
    assert first == second
    assert first <= 8

"""Sales metrics aggregates, isolation, and bounded queries."""

from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.permissions import UserRole
from app.models.campaign import MarketingCampaign
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


def test_sales_metrics_definitions_and_filters(client: TestClient, db: Session) -> None:
    owner = make_user(db, email="owner-sales@example.com", first_name="Olivia", last_name="Owner")
    outsider = make_user(
        db,
        email="outsider-sales@example.com",
        first_name="Other",
        last_name="User",
    )
    company = make_company(db, name="Sales A")
    elsewhere = make_company(db, name="Sales B")
    denied = make_company(db, name="Sales C")
    make_membership(db, owner, company, UserRole.OWNER)
    make_membership(db, owner, elsewhere, UserRole.OWNER)
    make_membership(db, outsider, elsewhere, UserRole.EMPLOYEE)
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
    pipeline = client.post(
        f"/api/companies/{company.id}/sales-pipelines",
        headers=headers,
        json={"name": "Default sales"},
    )
    assert pipeline.status_code == 201
    pipeline_id = pipeline.json()["id"]
    stage = client.post(
        f"/api/companies/{company.id}/sales-pipelines/{pipeline_id}/stages",
        headers=headers,
        json={"name": "Qualified"},
    )
    assert stage.status_code == 201
    stage_id = stage.json()["id"]
    other_pipeline = client.post(
        f"/api/companies/{elsewhere.id}/sales-pipelines",
        headers=headers,
        json={"name": "Hidden pipeline"},
    )
    other_stage = client.post(
        f"/api/companies/{elsewhere.id}/sales-pipelines/{other_pipeline.json()['id']}/stages",
        headers=headers,
        json={"name": "Hidden stage"},
    )
    tomorrow = date.today() + timedelta(days=1)
    yesterday = date.today() - timedelta(days=1)
    specs = [
        ("converted", Decimal("100.00"), "website", campaign.id, owner.id, tomorrow, None, None),
        ("lost", Decimal("40.00"), "google", None, None, yesterday, None, None),
        ("new", None, "website", None, None, yesterday, None, None),
        ("new", Decimal("0.00"), "manual", None, owner.id, tomorrow, pipeline_id, stage_id),
        ("archived", Decimal("999.00"), "website", campaign.id, owner.id, tomorrow, None, None),
    ]
    for status, value, source, campaign_id, assignee, close_on, pipe, stage_ref in specs:
        db.add(
            Lead(
                company_id=company.id,
                title=f"{status} deal",
                status=status,
                source=source,
                priority="medium",
                campaign_id=campaign_id,
                assigned_to_user_id=assignee,
                estimated_value=value,
                expected_close_date=close_on,
                pipeline_id=UUID(pipe) if pipe else None,
                pipeline_stage_id=UUID(stage_ref) if stage_ref else None,
            )
        )
    db.add(
        Lead(
            company_id=elsewhere.id,
            title="Secret deal",
            status="converted",
            source="facebook",
            priority="high",
            campaign_id=hidden.id,
            estimated_value=Decimal("500.00"),
        )
    )
    db.commit()
    path = f"/api/companies/{company.id}/sales-metrics"
    metrics = client.get(path, headers=headers)
    assert metrics.status_code == 200
    body = metrics.json()
    assert body["summary"] == {
        "total_opportunities": 4,
        "total_pipeline_value": "140.00",
        "converted_leads": 1,
        "converted_value": "100.00",
        "lost_leads": 1,
        "lost_value": "40.00",
        "conversion_rate": "25.00",
        "average_opportunity_value": "46.67",
    }
    assert body["expected_close"] == {
        "upcoming_count": 1,
        "upcoming_value": "0.00",
        "overdue_count": 1,
        "overdue_value": "0.00",
    }
    assert body["sales_cycle"]["available"] is False
    assert "conversion timestamp" in body["sales_cycle"]["reason"]
    assert body["interval"] == "month"
    stages = {item["stage_name"]: item for item in body["by_stage"]}
    assert stages["Qualified"]["lead_count"] == 1
    assert stages["Qualified"]["pipeline_value"] == "0.00"
    assert stages[None]["lead_count"] == 3
    sources = {item["source"]: item for item in body["by_source"]}
    assert sources["website"]["lead_count"] == 2
    assert sources["website"]["converted_value"] == "100.00"
    assert "facebook" not in sources
    campaigns = {item["campaign_name"]: item for item in body["by_campaign"]}
    assert campaigns["Spring wash"]["converted_count"] == 1
    assert "Secret campaign" not in campaigns
    users = {item["user_name"]: item for item in body["by_assigned_user"]}
    assert users["Olivia Owner"]["opportunity_count"] == 2
    assert "Secret deal" not in metrics.text
    assert "title" not in body["summary"]

    website = client.get(path, headers=headers, params={"source": "website"})
    assert website.json()["summary"]["total_opportunities"] == 2
    piped = client.get(
        path,
        headers=headers,
        params={"pipeline_id": pipeline_id, "stage_id": stage_id},
    )
    assert piped.json()["summary"]["total_opportunities"] == 1
    assigned = client.get(path, headers=headers, params={"assigned_to_user_id": str(owner.id)})
    assert assigned.json()["summary"]["total_opportunities"] == 2
    attributed = client.get(path, headers=headers, params={"campaign_id": str(campaign.id)})
    assert attributed.json()["summary"]["converted_leads"] == 1
    empty = client.get(
        path,
        headers=headers,
        params={"date_from": "2099-01-01", "date_to": "2099-01-02"},
    )
    assert empty.json()["summary"]["total_opportunities"] == 0
    assert empty.json()["summary"]["conversion_rate"] == "0.00"
    assert empty.json()["summary"]["average_opportunity_value"] == "0.00"
    assert empty.json()["trend"] == []
    assert client.get(
        path,
        headers=headers,
        params={"date_from": "2026-02-02", "date_to": "2026-02-01"},
    ).status_code == 400
    assert client.get(
        path,
        headers=headers,
        params={"pipeline_id": other_pipeline.json()["id"]},
    ).status_code == 404
    hidden_stage = client.get(path, headers=headers, params={"stage_id": other_stage.json()["id"]})
    assert hidden_stage.status_code == 404
    assert "Hidden stage" not in hidden_stage.text
    assert client.get(
        path,
        headers=headers,
        params={"campaign_id": str(hidden.id)},
    ).status_code == 404
    assert client.get(
        path,
        headers=headers,
        params={"assigned_to_user_id": str(outsider.id)},
    ).status_code == 400
    denied_metrics = client.get(f"/api/companies/{denied.id}/sales-metrics", headers=headers)
    assert denied_metrics.status_code == 403
    elsewhere_metrics = client.get(f"/api/companies/{elsewhere.id}/sales-metrics", headers=headers)
    assert elsewhere_metrics.status_code == 200
    assert elsewhere_metrics.json()["summary"]["total_pipeline_value"] == "500.00"


def test_sales_metrics_roles_and_query_count(
    client: TestClient,
    db: Session,
    engine: Engine,
) -> None:
    owner = make_user(db, email="owner-sales-count@example.com")
    manager = make_user(db, email="manager-sales@example.com")
    marketer = make_user(db, email="marketer-sales@example.com")
    employee = make_user(db, email="employee-sales@example.com")
    admin = make_user(db, email="root-sales@example.com", is_super_admin=True)
    company = make_company(db, name="Counted Sales")
    make_membership(db, owner, company, UserRole.OWNER)
    make_membership(db, manager, company, UserRole.COMPANY_MANAGER)
    make_membership(db, marketer, company, UserRole.MARKETING_MANAGER)
    make_membership(db, employee, company, UserRole.EMPLOYEE)
    for index in range(40):
        db.add(
            Lead(
                company_id=company.id,
                title=f"Deal {index}",
                status="converted" if index % 4 == 0 else "new",
                source="manual" if index % 2 == 0 else "google",
                priority="medium",
                estimated_value=Decimal("10.00") if index % 3 else None,
                created_at=datetime.now(UTC) - timedelta(days=index % 10),
            )
        )
    db.commit()
    path = f"/api/companies/{company.id}/sales-metrics"
    headers = auth_header(owner)

    def load(expected: int) -> None:
        response = client.get(path, headers=headers)
        assert response.status_code == 200
        assert response.json()["summary"]["total_opportunities"] == expected
        assert "items" not in response.json()

    db.expire_all()
    first = len(_selects(engine, lambda: load(40)))
    for index in range(40):
        db.add(
            Lead(
                company_id=company.id,
                title=f"More {index}",
                status="lost",
                source="referral",
                priority="low",
                estimated_value=Decimal("5.00"),
            )
        )
    db.commit()
    db.expire_all()
    second = len(_selects(engine, lambda: load(80)))
    assert first == second == 9
    assert client.get(path, headers=auth_header(manager)).status_code == 200
    assert client.get(path, headers=auth_header(marketer)).status_code == 403
    assert client.get(path, headers=auth_header(employee)).status_code == 403
    assert client.get(path, headers=auth_header(admin)).status_code == 200

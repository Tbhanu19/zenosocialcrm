"""Company-scoped sales metrics.

Every figure is a SQL aggregate. Lead rows are not loaded.
Converted and lost follow lead status. Pipeline stage names are not wins or losses.
"""

from datetime import UTC, date, datetime, time
from uuid import UUID

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.core.exceptions import BadRequestError, NotFoundError
from app.core.permissions import LeadSource, LeadStatus, MembershipStatus
from app.models.campaign import MarketingCampaign
from app.models.lead import Lead
from app.models.pipeline import SalesPipeline
from app.models.pipeline_stage import SalesPipelineStage
from app.models.user import User
from app.models.user_company import UserCompany
from app.schemas.metrics import rate_text
from app.schemas.sales_metrics import (
    ExpectedCloseMetrics,
    SalesCampaignMetric,
    SalesCycleStatus,
    SalesMetrics,
    SalesMetricSummary,
    SalesSourceMetric,
    SalesStageMetric,
    SalesTrendPoint,
    SalesUserMetric,
    average_amount,
    money_amount,
)
from app.services.metrics_service import _bucket, _interval

_SALES_CYCLE_REASON = (
    "A conversion timestamp is not stored, so sales cycle days cannot be calculated."
)


def sales_metrics(
    db: Session,
    company_id: UUID,
    *,
    date_from: date | None,
    date_to: date | None,
    pipeline_id: UUID | None,
    stage_id: UUID | None,
    assigned_to_user_id: UUID | None,
    source: LeadSource | None,
    campaign_id: UUID | None,
) -> SalesMetrics:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise BadRequestError("Date from must be on or before date to.")
    _require_pipeline(db, company_id, pipeline_id)
    _require_stage(db, company_id, pipeline_id, stage_id)
    _require_campaign(db, company_id, campaign_id)
    _require_member(db, company_id, assigned_to_user_id)
    filters = _filters(
        company_id,
        date_from,
        date_to,
        pipeline_id,
        stage_id,
        assigned_to_user_id,
        source,
        campaign_id,
    )
    summary, expected_close = _summary(db, filters)
    interval = _interval(date_from, date_to)
    return SalesMetrics(
        interval=interval,
        summary=summary,
        by_stage=_by_stage(db, filters),
        by_source=_by_source(db, filters),
        by_campaign=_by_campaign(db, filters),
        by_assigned_user=_by_user(db, filters),
        trend=_trend(db, filters, interval),
        expected_close=expected_close,
        sales_cycle=SalesCycleStatus(available=False, reason=_SALES_CYCLE_REASON),
    )


def _summary(
    db: Session,
    filters: list[ColumnElement[bool]],
) -> tuple[SalesMetricSummary, ExpectedCloseMetrics]:
    today = datetime.now(UTC).date()
    open_lead = Lead.status.notin_((LeadStatus.CONVERTED.value, LeadStatus.LOST.value))
    upcoming = and_(
        open_lead,
        Lead.expected_close_date.is_not(None),
        Lead.expected_close_date >= today,
    )
    overdue = and_(
        open_lead,
        Lead.expected_close_date.is_not(None),
        Lead.expected_close_date < today,
    )
    row = db.execute(
        select(
            func.count(),
            func.coalesce(func.sum(Lead.estimated_value), 0),
            _count_when(LeadStatus.CONVERTED.value),
            _value_when(LeadStatus.CONVERTED.value),
            _count_when(LeadStatus.LOST.value),
            _value_when(LeadStatus.LOST.value),
            func.count(Lead.estimated_value),
            func.coalesce(func.sum(case((upcoming, 1), else_=0)), 0),
            func.coalesce(
                func.sum(case((upcoming, func.coalesce(Lead.estimated_value, 0)), else_=0)),
                0,
            ),
            func.coalesce(func.sum(case((overdue, 1), else_=0)), 0),
            func.coalesce(
                func.sum(case((overdue, func.coalesce(Lead.estimated_value, 0)), else_=0)),
                0,
            ),
        ).where(*filters)
    ).one()
    total = int(row[0])
    converted = int(row[2])
    valued = int(row[6])
    summary = SalesMetricSummary(
        total_opportunities=total,
        total_pipeline_value=money_amount(row[1]),
        converted_leads=converted,
        converted_value=money_amount(row[3]),
        lost_leads=int(row[4]),
        lost_value=money_amount(row[5]),
        conversion_rate=rate_text(converted, total),
        average_opportunity_value=average_amount(row[1], valued),
    )
    expected = ExpectedCloseMetrics(
        upcoming_count=int(row[7]),
        upcoming_value=money_amount(row[8]),
        overdue_count=int(row[9]),
        overdue_value=money_amount(row[10]),
    )
    return summary, expected


def _by_stage(db: Session, filters: list[ColumnElement[bool]]) -> list[SalesStageMetric]:
    rows = db.execute(
        select(
            Lead.pipeline_stage_id,
            SalesPipelineStage.name,
            SalesPipelineStage.position,
            func.count(),
            func.coalesce(func.sum(Lead.estimated_value), 0),
            _count_when(LeadStatus.CONVERTED.value),
            _value_when(LeadStatus.CONVERTED.value),
        )
        .outerjoin(SalesPipelineStage, SalesPipelineStage.id == Lead.pipeline_stage_id)
        .where(*filters)
        .group_by(Lead.pipeline_stage_id, SalesPipelineStage.name, SalesPipelineStage.position)
        .order_by(
            case((SalesPipelineStage.position.is_(None), 1), else_=0),
            SalesPipelineStage.position.asc(),
            Lead.pipeline_stage_id.asc(),
        )
    ).all()
    return [
        SalesStageMetric(
            stage_id=stage_id,
            stage_name=name,
            position=position,
            lead_count=int(lead_count),
            pipeline_value=money_amount(value),
            converted_count=int(converted_count),
            converted_value=money_amount(converted_value),
        )
        for stage_id, name, position, lead_count, value, converted_count, converted_value in rows
    ]


def _by_source(db: Session, filters: list[ColumnElement[bool]]) -> list[SalesSourceMetric]:
    rows = db.execute(
        select(
            Lead.source,
            func.count(),
            func.coalesce(func.sum(Lead.estimated_value), 0),
            _count_when(LeadStatus.CONVERTED.value),
            _value_when(LeadStatus.CONVERTED.value),
        )
        .where(*filters)
        .group_by(Lead.source)
        .order_by(func.count().desc(), Lead.source.asc())
    ).all()
    return [
        SalesSourceMetric(
            source=LeadSource(source),
            lead_count=int(lead_count),
            pipeline_value=money_amount(value),
            converted_count=int(converted_count),
            converted_value=money_amount(converted_value),
        )
        for source, lead_count, value, converted_count, converted_value in rows
    ]


def _by_campaign(db: Session, filters: list[ColumnElement[bool]]) -> list[SalesCampaignMetric]:
    rows = db.execute(
        select(
            Lead.campaign_id,
            MarketingCampaign.name,
            func.count(),
            func.coalesce(func.sum(Lead.estimated_value), 0),
            _count_when(LeadStatus.CONVERTED.value),
            _value_when(LeadStatus.CONVERTED.value),
        )
        .outerjoin(MarketingCampaign, MarketingCampaign.id == Lead.campaign_id)
        .where(*filters)
        .group_by(Lead.campaign_id, MarketingCampaign.name)
        .order_by(func.count().desc(), Lead.campaign_id.asc())
    ).all()
    return [
        SalesCampaignMetric(
            campaign_id=campaign_id,
            campaign_name=name,
            lead_count=int(lead_count),
            pipeline_value=money_amount(value),
            converted_count=int(converted_count),
            converted_value=money_amount(converted_value),
        )
        for campaign_id, name, lead_count, value, converted_count, converted_value in rows
    ]


def _by_user(db: Session, filters: list[ColumnElement[bool]]) -> list[SalesUserMetric]:
    rows = db.execute(
        select(
            Lead.assigned_to_user_id,
            User.first_name,
            User.last_name,
            func.count(),
            func.coalesce(func.sum(Lead.estimated_value), 0),
            _count_when(LeadStatus.CONVERTED.value),
            _value_when(LeadStatus.CONVERTED.value),
        )
        .outerjoin(User, User.id == Lead.assigned_to_user_id)
        .where(*filters)
        .group_by(Lead.assigned_to_user_id, User.first_name, User.last_name)
        .order_by(func.count().desc(), Lead.assigned_to_user_id.asc())
    ).all()
    return [
        SalesUserMetric(
            user_id=user_id,
            user_name=_person(first_name, last_name),
            opportunity_count=int(count),
            pipeline_value=money_amount(value),
            converted_count=int(converted_count),
            converted_value=money_amount(converted_value),
        )
        for user_id, first_name, last_name, count, value, converted_count, converted_value in rows
    ]


def _trend(
    db: Session,
    filters: list[ColumnElement[bool]],
    interval: str,
) -> list[SalesTrendPoint]:
    bucket = _bucket(db, interval)
    rows = db.execute(
        select(
            bucket.label("period"),
            func.count(),
            func.coalesce(func.sum(Lead.estimated_value), 0),
            _count_when(LeadStatus.CONVERTED.value),
            _value_when(LeadStatus.CONVERTED.value),
        )
        .where(*filters)
        .group_by(bucket)
        .order_by(bucket.asc())
    ).all()
    return [
        SalesTrendPoint(
            period=str(period),
            opportunity_count=int(count),
            pipeline_value=money_amount(value),
            converted_count=int(converted_count),
            converted_value=money_amount(converted_value),
        )
        for period, count, value, converted_count, converted_value in rows
        if period is not None
    ]


def _filters(
    company_id: UUID,
    date_from: date | None,
    date_to: date | None,
    pipeline_id: UUID | None,
    stage_id: UUID | None,
    assigned_to_user_id: UUID | None,
    source: LeadSource | None,
    campaign_id: UUID | None,
) -> list[ColumnElement[bool]]:
    filters: list[ColumnElement[bool]] = [
        Lead.company_id == company_id,
        Lead.status != LeadStatus.ARCHIVED.value,
    ]
    if pipeline_id is not None:
        filters.append(Lead.pipeline_id == pipeline_id)
    if stage_id is not None:
        filters.append(Lead.pipeline_stage_id == stage_id)
    if assigned_to_user_id is not None:
        filters.append(Lead.assigned_to_user_id == assigned_to_user_id)
    if source is not None:
        filters.append(Lead.source == source.value)
    if campaign_id is not None:
        filters.append(Lead.campaign_id == campaign_id)
    if date_from is not None:
        filters.append(Lead.created_at >= datetime.combine(date_from, time.min, tzinfo=UTC))
    if date_to is not None:
        filters.append(Lead.created_at <= datetime.combine(date_to, time.max, tzinfo=UTC))
    return filters


def _count_when(status: str) -> ColumnElement[int]:
    return func.coalesce(func.sum(case((Lead.status == status, 1), else_=0)), 0)


def _value_when(status: str) -> ColumnElement[object]:
    return func.coalesce(
        func.sum(
            case(
                (Lead.status == status, func.coalesce(Lead.estimated_value, 0)),
                else_=0,
            )
        ),
        0,
    )


def _require_pipeline(db: Session, company_id: UUID, pipeline_id: UUID | None) -> None:
    if pipeline_id is None:
        return
    found = db.scalar(
        select(SalesPipeline.id).where(
            SalesPipeline.company_id == company_id,
            SalesPipeline.id == pipeline_id,
        )
    )
    if found is None:
        raise NotFoundError("Pipeline not found.")


def _require_stage(
    db: Session,
    company_id: UUID,
    pipeline_id: UUID | None,
    stage_id: UUID | None,
) -> None:
    if stage_id is None:
        return
    found_pipeline = db.scalar(
        select(SalesPipelineStage.pipeline_id)
        .join(SalesPipeline, SalesPipeline.id == SalesPipelineStage.pipeline_id)
        .where(
            SalesPipelineStage.id == stage_id,
            SalesPipeline.company_id == company_id,
        )
    )
    if found_pipeline is None or (pipeline_id is not None and found_pipeline != pipeline_id):
        raise NotFoundError("Stage not found.")


def _require_campaign(db: Session, company_id: UUID, campaign_id: UUID | None) -> None:
    if campaign_id is None:
        return
    found = db.scalar(
        select(MarketingCampaign.id).where(
            MarketingCampaign.company_id == company_id,
            MarketingCampaign.id == campaign_id,
        )
    )
    if found is None:
        raise NotFoundError("Campaign not found.")


def _require_member(db: Session, company_id: UUID, user_id: UUID | None) -> None:
    if user_id is None:
        return
    found = db.scalar(
        select(UserCompany.id).where(
            UserCompany.company_id == company_id,
            UserCompany.user_id == user_id,
            UserCompany.status == MembershipStatus.ACTIVE.value,
        )
    )
    if found is None:
        raise BadRequestError("That person is not a member of this company.")


def _person(first_name: str | None, last_name: str | None) -> str | None:
    if first_name is None or last_name is None:
        return None
    return f"{first_name} {last_name}"

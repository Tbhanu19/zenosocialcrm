"""Company-scoped lead metrics.

Every figure is a SQL aggregate. Lead rows are not loaded.
"""

from datetime import UTC, date, datetime, time
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.core.permissions import LeadSource, LeadStatus
from app.models.campaign import MarketingCampaign
from app.models.lead import Lead
from app.schemas.metrics import (
    LeadCampaignCount,
    LeadMetrics,
    LeadMetricSummary,
    LeadSourceCount,
    LeadStatusCount,
    LeadTimePoint,
    rate_text,
)

_OPEN_STATUSES = (
    LeadStatus.NEW,
    LeadStatus.CONTACTED,
    LeadStatus.QUALIFIED,
    LeadStatus.UNQUALIFIED,
    LeadStatus.CONVERTED,
    LeadStatus.LOST,
)


def lead_metrics(
    db: Session,
    company_id: UUID,
    *,
    date_from: date | None,
    date_to: date | None,
    source: LeadSource | None,
    campaign_id: UUID | None,
    assigned_to_user_id: UUID | None,
    status: LeadStatus | None,
) -> LeadMetrics:
    filters = _filters(
        company_id,
        date_from,
        date_to,
        source,
        campaign_id,
        assigned_to_user_id,
        status,
    )
    summary, by_status = _summary(db, filters)
    by_source = _by_source(db, filters)
    by_campaign = _by_campaign(db, filters)
    interval = _interval(date_from, date_to)
    over_time = _over_time(db, filters, interval)
    return LeadMetrics(
        interval=interval,
        summary=summary,
        by_status=by_status,
        by_source=by_source,
        by_campaign=by_campaign,
        over_time=over_time,
    )


def _summary(
    db: Session,
    filters: list[ColumnElement[bool]],
) -> tuple[LeadMetricSummary, list[LeadStatusCount]]:
    columns = [
        func.coalesce(func.sum(case((Lead.status == item.value, 1), else_=0)), 0)
        for item in _OPEN_STATUSES
    ]
    row = db.execute(
        select(
            func.count(),
            *columns,
        ).where(*filters)
    ).one()
    total = int(row[0])
    counts = {status: int(row[index + 1]) for index, status in enumerate(_OPEN_STATUSES)}
    converted = counts[LeadStatus.CONVERTED]
    summary = LeadMetricSummary(
        total_leads=total,
        new_leads=counts[LeadStatus.NEW],
        contacted_leads=counts[LeadStatus.CONTACTED],
        qualified_leads=counts[LeadStatus.QUALIFIED],
        unqualified_leads=counts[LeadStatus.UNQUALIFIED],
        converted_leads=converted,
        lost_leads=counts[LeadStatus.LOST],
        conversion_rate=rate_text(converted, total),
    )
    by_status = [LeadStatusCount(status=status, count=counts[status]) for status in _OPEN_STATUSES]
    return summary, by_status


def _by_source(db: Session, filters: list[ColumnElement[bool]]) -> list[LeadSourceCount]:
    rows = db.execute(
        select(Lead.source, func.count())
        .where(*filters)
        .group_by(Lead.source)
        .order_by(func.count().desc(), Lead.source.asc())
    ).all()
    return [LeadSourceCount(source=LeadSource(source), count=int(count)) for source, count in rows]


def _by_campaign(db: Session, filters: list[ColumnElement[bool]]) -> list[LeadCampaignCount]:
    converted = func.coalesce(
        func.sum(case((Lead.status == LeadStatus.CONVERTED.value, 1), else_=0)),
        0,
    )
    rows = db.execute(
        select(
            Lead.campaign_id,
            MarketingCampaign.name,
            func.count(),
            converted,
        )
        .outerjoin(MarketingCampaign, MarketingCampaign.id == Lead.campaign_id)
        .where(*filters)
        .group_by(Lead.campaign_id, MarketingCampaign.name)
        .order_by(func.count().desc(), Lead.campaign_id.asc())
    ).all()
    return [
        LeadCampaignCount(
            campaign_id=campaign_id,
            campaign_name=name,
            lead_count=int(lead_count),
            converted_count=int(converted_count),
        )
        for campaign_id, name, lead_count, converted_count in rows
    ]


def _over_time(
    db: Session,
    filters: list[ColumnElement[bool]],
    interval: str,
) -> list[LeadTimePoint]:
    bucket = _bucket(db, interval)
    converted = func.coalesce(
        func.sum(case((Lead.status == LeadStatus.CONVERTED.value, 1), else_=0)),
        0,
    )
    rows = db.execute(
        select(bucket.label("period"), func.count(), converted)
        .where(*filters)
        .group_by(bucket)
        .order_by(bucket.asc())
    ).all()
    return [
        LeadTimePoint(
            period=str(period),
            lead_count=int(lead_count),
            converted_count=int(converted_count),
        )
        for period, lead_count, converted_count in rows
        if period is not None
    ]


def _filters(
    company_id: UUID,
    date_from: date | None,
    date_to: date | None,
    source: LeadSource | None,
    campaign_id: UUID | None,
    assigned_to_user_id: UUID | None,
    status: LeadStatus | None,
) -> list[ColumnElement[bool]]:
    filters: list[ColumnElement[bool]] = [Lead.company_id == company_id]
    if status is None:
        filters.append(Lead.status != LeadStatus.ARCHIVED.value)
    else:
        filters.append(Lead.status == status.value)
    if source is not None:
        filters.append(Lead.source == source.value)
    if campaign_id is not None:
        filters.append(Lead.campaign_id == campaign_id)
    if assigned_to_user_id is not None:
        filters.append(Lead.assigned_to_user_id == assigned_to_user_id)
    if date_from is not None:
        filters.append(Lead.created_at >= datetime.combine(date_from, time.min, tzinfo=UTC))
    if date_to is not None:
        filters.append(Lead.created_at <= datetime.combine(date_to, time.max, tzinfo=UTC))
    return filters


def _interval(date_from: date | None, date_to: date | None) -> str:
    """Day for a month or less, week through six months, otherwise month."""
    if date_from is None or date_to is None:
        if date_from is None and date_to is None:
            return "month"
        anchor = date_from or date_to
        assert anchor is not None
        other = datetime.now(UTC).date()
        span = abs((other - anchor).days)
    else:
        span = abs((date_to - date_from).days)
    if span <= 31:
        return "day"
    if span <= 180:
        return "week"
    return "month"


def _bucket(db: Session, interval: str) -> ColumnElement[str]:
    dialect = db.get_bind().dialect.name
    created = Lead.created_at
    if interval == "day":
        return func.date(created)
    if interval == "week":
        if dialect == "mysql":
            return func.date_format(created, "%x-W%v")
        return func.strftime("%Y-W%W", created)
    if dialect == "mysql":
        return func.date_format(created, "%Y-%m")
    return func.strftime("%Y-%m", created)

"""Company-scoped marketing campaigns."""

import logging
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.core.exceptions import BadRequestError, NotFoundError
from app.core.permissions import CampaignChannel, CampaignStatus, CampaignType
from app.core.search import contains_pattern
from app.models.campaign import MarketingCampaign
from app.models.user import User
from app.schemas.campaign import (
    CampaignCreate,
    CampaignListItem,
    CampaignRead,
    CampaignUpdate,
)
from app.schemas.pagination import Page, total_pages

logger = logging.getLogger("zenosocialcrm.marketing")


def list_campaigns(
    db: Session,
    company_id: UUID,
    *,
    page: int,
    page_size: int,
    search: str | None,
    status: CampaignStatus | None,
    channel: CampaignChannel | None,
    campaign_type: CampaignType | None,
    start_date: date | None,
    end_date: date | None,
) -> Page[CampaignListItem]:
    filters = _filters(
        company_id,
        search,
        status,
        channel,
        campaign_type,
        start_date,
        end_date,
    )
    total = db.scalar(select(func.count()).select_from(MarketingCampaign).where(*filters)) or 0
    rows = db.scalars(
        select(MarketingCampaign)
        .where(*filters)
        .order_by(MarketingCampaign.created_at.desc(), MarketingCampaign.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page(
        items=[_list_item(campaign) for campaign in rows],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages(total, page_size),
    )


def get_campaign(db: Session, company_id: UUID, campaign_id: UUID) -> CampaignRead:
    row = db.execute(
        select(MarketingCampaign, User.first_name, User.last_name)
        .outerjoin(User, User.id == MarketingCampaign.created_by_user_id)
        .where(
            MarketingCampaign.company_id == company_id,
            MarketingCampaign.id == campaign_id,
        )
    ).one_or_none()
    if row is None:
        raise NotFoundError("Campaign not found.")
    campaign, first_name, last_name = row
    return _detail(campaign, first_name, last_name)


def create_campaign(
    db: Session,
    actor_id: UUID,
    company_id: UUID,
    data: CampaignCreate,
) -> CampaignRead:
    campaign = MarketingCampaign(
        company_id=company_id,
        name=data.name,
        description=data.description,
        campaign_type=data.campaign_type.value,
        channel=data.channel.value,
        status=data.status.value,
        start_date=data.start_date,
        end_date=data.end_date,
        budget=data.budget,
        source=data.source,
        external_campaign_id=data.external_campaign_id,
        notes=data.notes,
        created_by_user_id=actor_id,
    )
    db.add(campaign)
    db.commit()
    logger.info(
        "campaign created actor_id=%s company_id=%s campaign_id=%s",
        actor_id,
        company_id,
        campaign.id,
    )
    return get_campaign(db, company_id, campaign.id)


def update_campaign(
    db: Session,
    actor_id: UUID,
    company_id: UUID,
    campaign_id: UUID,
    data: CampaignUpdate,
) -> CampaignRead:
    if not data.model_fields_set:
        raise BadRequestError("At least one field is required.")
    campaign = db.scalar(
        select(MarketingCampaign).where(
            MarketingCampaign.company_id == company_id,
            MarketingCampaign.id == campaign_id,
        )
    )
    if campaign is None:
        raise NotFoundError("Campaign not found.")
    try:
        for field in data.model_fields_set:
            value = getattr(data, field)
            if field in {"name", "campaign_type", "channel", "status"} and value is None:
                raise BadRequestError("Name, type, channel, and status cannot be cleared.")
            if field in {"campaign_type", "channel", "status"}:
                value = value.value
            setattr(campaign, field, value)
        _require_date_order(campaign.start_date, campaign.end_date)
    except BadRequestError:
        db.rollback()
        raise
    db.commit()
    logger.info(
        "campaign updated actor_id=%s company_id=%s campaign_id=%s",
        actor_id,
        company_id,
        campaign.id,
    )
    return get_campaign(db, company_id, campaign.id)


def _filters(
    company_id: UUID,
    search: str | None,
    status: CampaignStatus | None,
    channel: CampaignChannel | None,
    campaign_type: CampaignType | None,
    start_date: date | None,
    end_date: date | None,
) -> list[ColumnElement[bool]]:
    filters: list[ColumnElement[bool]] = [MarketingCampaign.company_id == company_id]
    if status is None:
        filters.append(MarketingCampaign.status != CampaignStatus.ARCHIVED.value)
    else:
        filters.append(MarketingCampaign.status == status.value)
    if channel is not None:
        filters.append(MarketingCampaign.channel == channel.value)
    if campaign_type is not None:
        filters.append(MarketingCampaign.campaign_type == campaign_type.value)
    if start_date is not None:
        filters.append(MarketingCampaign.start_date >= start_date)
    if end_date is not None:
        filters.append(MarketingCampaign.end_date <= end_date)
    term = (search or "").strip()
    if term:
        pattern = contains_pattern(term)
        filters.append(
            or_(
                MarketingCampaign.name.ilike(pattern, escape="\\"),
                MarketingCampaign.description.ilike(pattern, escape="\\"),
                MarketingCampaign.source.ilike(pattern, escape="\\"),
                MarketingCampaign.external_campaign_id.ilike(pattern, escape="\\"),
            )
        )
    return filters


def _require_date_order(start_date: date | None, end_date: date | None) -> None:
    if start_date is not None and end_date is not None and end_date < start_date:
        raise BadRequestError("End date must be on or after the start date.")


def _list_item(campaign: MarketingCampaign) -> CampaignListItem:
    return CampaignListItem(
        id=campaign.id,
        name=campaign.name,
        campaign_type=CampaignType(campaign.campaign_type),
        channel=CampaignChannel(campaign.channel),
        status=CampaignStatus(campaign.status),
        start_date=campaign.start_date,
        end_date=campaign.end_date,
        budget=money_text(campaign.budget),
        source=campaign.source,
        created_at=campaign.created_at,
    )


def _detail(
    campaign: MarketingCampaign,
    first_name: str | None,
    last_name: str | None,
) -> CampaignRead:
    listed = _list_item(campaign)
    return CampaignRead(
        **listed.model_dump(),
        description=campaign.description,
        external_campaign_id=campaign.external_campaign_id,
        notes=campaign.notes,
        created_by_user_id=campaign.created_by_user_id,
        creator_name=_person_name(first_name, last_name),
        updated_at=campaign.updated_at,
    )


def money_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return f"{Decimal(value):.2f}"


def _person_name(first_name: str | None, last_name: str | None) -> str | None:
    if first_name is None or last_name is None:
        return None
    return f"{first_name} {last_name}"

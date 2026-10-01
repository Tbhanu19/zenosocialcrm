"""Company-scoped leads.

Contact, campaign, and assignee names are joined into each list query.
"""

import logging
from datetime import UTC, date, datetime, time
from uuid import UUID

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session, aliased
from sqlalchemy.sql.elements import ColumnElement

from app.core.exceptions import BadRequestError, NotFoundError
from app.core.permissions import (
    CampaignStatus,
    LeadBusinessType,
    LeadPriority,
    LeadSource,
    LeadStatus,
    MembershipStatus,
    PreferredContactType,
)
from app.core.search import contains_pattern
from app.models.campaign import MarketingCampaign
from app.models.contact import Contact
from app.models.lead import Lead
from app.models.pipeline import SalesPipeline
from app.models.pipeline_stage import SalesPipelineStage
from app.models.user import User
from app.models.user_company import UserCompany
from app.schemas.campaign import MarketingSummary
from app.schemas.lead import LeadCreate, LeadListItem, LeadRead, LeadUpdate
from app.schemas.pagination import Page, total_pages
from app.services.campaign_service import money_text

logger = logging.getLogger("zenosocialcrm.leads")


def list_leads(
    db: Session,
    company_id: UUID,
    *,
    page: int,
    page_size: int,
    search: str | None,
    status: LeadStatus | None,
    source: LeadSource | None,
    priority: LeadPriority | None,
    campaign_id: UUID | None,
    assigned_to: UUID | None,
    created_from: date | None,
    created_to: date | None,
) -> Page[LeadListItem]:
    filters = _filters(
        company_id,
        search,
        status,
        source,
        priority,
        campaign_id,
        assigned_to,
        created_from,
        created_to,
    )
    count_stmt = select(func.count()).select_from(Lead)
    if _needs_contact_join(search):
        count_stmt = count_stmt.outerjoin(Contact, Contact.id == Lead.contact_id)
    total = db.scalar(count_stmt.where(*filters)) or 0
    assignee = aliased(User)
    rows = db.execute(
        select(
            Lead,
            Contact.first_name,
            Contact.last_name,
            MarketingCampaign.name,
            MarketingCampaign.status,
            assignee.first_name,
            assignee.last_name,
        )
        .outerjoin(Contact, Contact.id == Lead.contact_id)
        .outerjoin(MarketingCampaign, MarketingCampaign.id == Lead.campaign_id)
        .outerjoin(assignee, assignee.id == Lead.assigned_to_user_id)
        .where(*filters)
        .order_by(Lead.created_at.desc(), Lead.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items = [
        _list_item(lead, contact_first, contact_last, campaign_name, campaign_status, first, last)
        for (
            lead,
            contact_first,
            contact_last,
            campaign_name,
            campaign_status,
            first,
            last,
        ) in rows
    ]
    return Page(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages(total, page_size),
    )


def get_lead(db: Session, company_id: UUID, lead_id: UUID) -> LeadRead:
    assignee = aliased(User)
    row = db.execute(
        select(
            Lead,
            Contact.first_name,
            Contact.last_name,
            MarketingCampaign.name,
            MarketingCampaign.status,
            assignee.first_name,
            assignee.last_name,
            SalesPipeline.name,
            SalesPipelineStage.name,
        )
        .outerjoin(Contact, Contact.id == Lead.contact_id)
        .outerjoin(MarketingCampaign, MarketingCampaign.id == Lead.campaign_id)
        .outerjoin(assignee, assignee.id == Lead.assigned_to_user_id)
        .outerjoin(SalesPipeline, SalesPipeline.id == Lead.pipeline_id)
        .outerjoin(SalesPipelineStage, SalesPipelineStage.id == Lead.pipeline_stage_id)
        .where(Lead.company_id == company_id, Lead.id == lead_id)
    ).one_or_none()
    if row is None:
        raise NotFoundError("Lead not found.")
    (
        lead,
        contact_first,
        contact_last,
        campaign_name,
        campaign_status,
        first,
        last,
        pipeline_name,
        stage_name,
    ) = row
    listed = _list_item(
        lead,
        contact_first,
        contact_last,
        campaign_name,
        campaign_status,
        first,
        last,
    )
    return LeadRead(
        **listed.model_dump(),
        description=lead.description,
        notes=lead.notes,
        expected_close_date=lead.expected_close_date,
        updated_at=lead.updated_at,
        pipeline_id=lead.pipeline_id,
        pipeline_stage_id=lead.pipeline_stage_id,
        pipeline_name=pipeline_name,
        stage_name=stage_name,
    )


def create_lead(
    db: Session,
    actor_id: UUID,
    company_id: UUID,
    data: LeadCreate,
) -> LeadRead:
    _require_contact(db, company_id, data.contact_id)
    _require_campaign(db, company_id, data.campaign_id)
    _require_active_member(db, company_id, data.assigned_to_user_id)
    lead = Lead(
        company_id=company_id,
        contact_id=data.contact_id,
        campaign_id=data.campaign_id,
        title=data.company_name or data.title,
        description=data.description,
        status=data.status.value,
        source=data.source.value,
        priority=data.priority.value,
        assigned_to_user_id=data.assigned_to_user_id,
        estimated_value=data.estimated_value,
        expected_close_date=data.expected_close_date,
        notes=data.notes,
        company_name=data.company_name,
        business_type=None if data.business_type is None else data.business_type.value,
        address=data.address,
        phone_number=data.phone_number,
        main_contact_name=data.main_contact_name,
        email=data.email,
        phone_number_2=data.phone_number_2,
        comments=data.comments,
    )
    db.add(lead)
    db.commit()
    logger.info(
        "lead created actor_id=%s company_id=%s lead_id=%s",
        actor_id,
        company_id,
        lead.id,
    )
    return get_lead(db, company_id, lead.id)


def update_lead(
    db: Session,
    actor_id: UUID,
    company_id: UUID,
    lead_id: UUID,
    data: LeadUpdate,
) -> LeadRead:
    if not data.model_fields_set:
        raise BadRequestError("At least one field is required.")
    lead = db.scalar(select(Lead).where(Lead.company_id == company_id, Lead.id == lead_id))
    if lead is None:
        raise NotFoundError("Lead not found.")
    if "contact_id" in data.model_fields_set:
        _require_contact(db, company_id, data.contact_id)
    if "campaign_id" in data.model_fields_set:
        _require_campaign(db, company_id, data.campaign_id)
    if "assigned_to_user_id" in data.model_fields_set:
        _require_active_member(db, company_id, data.assigned_to_user_id)
    try:
        for field in data.model_fields_set:
            value = getattr(data, field)
            if field in {"title", "status", "source", "priority"} and value is None:
                raise BadRequestError("Title, status, source, and priority cannot be cleared.")
            if field in {
                "status",
                "source",
                "priority",
                "business_type",
                "preferred_contact_type",
            } and value is not None:
                value = value.value
            setattr(lead, field, value)
            if field == "company_name" and isinstance(value, str):
                lead.title = value
    except BadRequestError:
        db.rollback()
        raise
    db.commit()
    logger.info(
        "lead updated actor_id=%s company_id=%s lead_id=%s",
        actor_id,
        company_id,
        lead.id,
    )
    return get_lead(db, company_id, lead.id)


def marketing_summary(db: Session, company_id: UUID) -> MarketingSummary:
    active_campaigns = (
        db.scalar(
            select(func.count())
            .select_from(MarketingCampaign)
            .where(
                MarketingCampaign.company_id == company_id,
                MarketingCampaign.status == CampaignStatus.ACTIVE.value,
            )
        )
        or 0
    )
    total, new_count, converted = db.execute(
        select(
            func.coalesce(
                func.sum(case((Lead.status != LeadStatus.ARCHIVED.value, 1), else_=0)),
                0,
            ),
            func.coalesce(func.sum(case((Lead.status == LeadStatus.NEW.value, 1), else_=0)), 0),
            func.coalesce(
                func.sum(case((Lead.status == LeadStatus.CONVERTED.value, 1), else_=0)),
                0,
            ),
        ).where(Lead.company_id == company_id)
    ).one()
    return MarketingSummary(
        active_campaigns=int(active_campaigns),
        total_leads=int(total),
        new_leads=int(new_count),
        converted_leads=int(converted),
    )


def _filters(
    company_id: UUID,
    search: str | None,
    status: LeadStatus | None,
    source: LeadSource | None,
    priority: LeadPriority | None,
    campaign_id: UUID | None,
    assigned_to: UUID | None,
    created_from: date | None,
    created_to: date | None,
) -> list[ColumnElement[bool]]:
    filters: list[ColumnElement[bool]] = [Lead.company_id == company_id]
    if status is None:
        filters.append(Lead.status != LeadStatus.ARCHIVED.value)
    else:
        filters.append(Lead.status == status.value)
    if source is not None:
        filters.append(Lead.source == source.value)
    if priority is not None:
        filters.append(Lead.priority == priority.value)
    if campaign_id is not None:
        filters.append(Lead.campaign_id == campaign_id)
    if assigned_to is not None:
        filters.append(Lead.assigned_to_user_id == assigned_to)
    if created_from is not None:
        filters.append(Lead.created_at >= datetime.combine(created_from, time.min, tzinfo=UTC))
    if created_to is not None:
        filters.append(Lead.created_at <= datetime.combine(created_to, time.max, tzinfo=UTC))
    term = (search or "").strip()
    if term:
        pattern = contains_pattern(term)
        filters.append(
            or_(
                Lead.title.ilike(pattern, escape="\\"),
                Lead.company_name.ilike(pattern, escape="\\"),
                Lead.main_contact_name.ilike(pattern, escape="\\"),
                Lead.email.ilike(pattern, escape="\\"),
                Lead.phone_number.ilike(pattern, escape="\\"),
                Lead.phone_number_2.ilike(pattern, escape="\\"),
                Lead.description.ilike(pattern, escape="\\"),
                Contact.first_name.ilike(pattern, escape="\\"),
                Contact.last_name.ilike(pattern, escape="\\"),
                Contact.email.ilike(pattern, escape="\\"),
                Contact.phone.ilike(pattern, escape="\\"),
            )
        )
    return filters


def _needs_contact_join(search: str | None) -> bool:
    return bool((search or "").strip())


def _require_contact(db: Session, company_id: UUID, contact_id: UUID | None) -> None:
    if contact_id is None:
        return
    found = db.scalar(
        select(Contact.id).where(Contact.id == contact_id, Contact.company_id == company_id)
    )
    if found is None:
        raise NotFoundError("Contact not found.")


def _require_campaign(db: Session, company_id: UUID, campaign_id: UUID | None) -> None:
    if campaign_id is None:
        return
    found = db.scalar(
        select(MarketingCampaign.id).where(
            MarketingCampaign.id == campaign_id,
            MarketingCampaign.company_id == company_id,
        )
    )
    if found is None:
        raise NotFoundError("Campaign not found.")


def _require_active_member(db: Session, company_id: UUID, user_id: UUID | None) -> None:
    if user_id is None:
        return
    membership_id = db.scalar(
        select(UserCompany.id).where(
            UserCompany.company_id == company_id,
            UserCompany.user_id == user_id,
            UserCompany.status == MembershipStatus.ACTIVE.value,
        )
    )
    if membership_id is None:
        raise BadRequestError("That person is not a member of this company.")


def _list_item(
    lead: Lead,
    contact_first: str | None,
    contact_last: str | None,
    campaign_name: str | None,
    campaign_status: str | None,
    assignee_first: str | None,
    assignee_last: str | None,
) -> LeadListItem:
    return LeadListItem(
        id=lead.id,
        title=lead.title,
        status=LeadStatus(lead.status),
        priority=LeadPriority(lead.priority),
        source=LeadSource(lead.source),
        contact_id=lead.contact_id,
        contact_name=_person_name(contact_first, contact_last),
        campaign_id=lead.campaign_id,
        campaign_name=campaign_name,
        campaign_status=None if campaign_status is None else CampaignStatus(campaign_status),
        assigned_to_user_id=lead.assigned_to_user_id,
        assignee_name=_person_name(assignee_first, assignee_last),
        estimated_value=money_text(lead.estimated_value),
        created_at=lead.created_at,
        company_name=lead.company_name,
        business_type=None if lead.business_type is None else LeadBusinessType(lead.business_type),
        address=lead.address,
        phone_number=lead.phone_number,
        main_contact_name=lead.main_contact_name,
        email=lead.email,
        phone_number_2=lead.phone_number_2,
        comments=lead.comments,
        preferred_contact_type=(
            None
            if lead.preferred_contact_type is None
            else PreferredContactType(lead.preferred_contact_type)
        ),
        pipeline_created_at=lead.pipeline_created_at,
    )


def _person_name(first_name: str | None, last_name: str | None) -> str | None:
    if first_name is None or last_name is None:
        return None
    return f"{first_name} {last_name}"

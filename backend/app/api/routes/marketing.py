"""Company-scoped marketing campaigns."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_crm_writer
from app.core.permissions import CampaignChannel, CampaignStatus, CampaignType, LeadStatus
from app.db.session import get_db
from app.models.user import User
from app.schemas.campaign import (
    CampaignCreate,
    CampaignListItem,
    CampaignRead,
    CampaignUpdate,
    MarketingSummary,
)
from app.schemas.lead import LeadListItem
from app.schemas.pagination import Page
from app.services.authorization_service import CompanyAccess
from app.services.campaign_service import (
    create_campaign,
    get_campaign,
    list_campaigns,
    update_campaign,
)
from app.services.lead_service import list_leads, marketing_summary

router = APIRouter(prefix="/companies/{company_id}/marketing", tags=["marketing"])


@router.get("/summary", response_model=MarketingSummary)
def marketing_summary_view(
    db: Session = Depends(get_db),
    access: CompanyAccess = Depends(require_crm_writer),
) -> MarketingSummary:
    return marketing_summary(db, access.company.id)


@router.get("/campaigns", response_model=Page[CampaignListItem])
def campaign_list(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=100),
    status: CampaignStatus | None = None,
    channel: CampaignChannel | None = None,
    campaign_type: CampaignType | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    access: CompanyAccess = Depends(require_crm_writer),
) -> Page[CampaignListItem]:
    return list_campaigns(
        db,
        access.company.id,
        page=page,
        page_size=page_size,
        search=search,
        status=status,
        channel=channel,
        campaign_type=campaign_type,
        start_date=start_date,
        end_date=end_date,
    )


@router.post("/campaigns", response_model=CampaignRead, status_code=201)
def campaign_create(
    body: CampaignCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
    access: CompanyAccess = Depends(require_crm_writer),
) -> CampaignRead:
    return create_campaign(db, actor.id, access.company.id, body)


@router.get("/campaigns/{campaign_id}/leads", response_model=Page[LeadListItem])
def campaign_leads(
    campaign_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: LeadStatus | None = None,
    db: Session = Depends(get_db),
    access: CompanyAccess = Depends(require_crm_writer),
) -> Page[LeadListItem]:
    get_campaign(db, access.company.id, campaign_id)
    return list_leads(
        db,
        access.company.id,
        page=page,
        page_size=page_size,
        search=None,
        status=status,
        source=None,
        priority=None,
        campaign_id=campaign_id,
        assigned_to=None,
        created_from=None,
        created_to=None,
    )


@router.get("/campaigns/{campaign_id}", response_model=CampaignRead)
def campaign_detail(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    access: CompanyAccess = Depends(require_crm_writer),
) -> CampaignRead:
    return get_campaign(db, access.company.id, campaign_id)


@router.patch("/campaigns/{campaign_id}", response_model=CampaignRead)
def campaign_update(
    campaign_id: UUID,
    body: CampaignUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
    access: CompanyAccess = Depends(require_crm_writer),
) -> CampaignRead:
    return update_campaign(db, actor.id, access.company.id, campaign_id, body)

"""Company-scoped leads."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_crm_writer
from app.core.permissions import LeadPriority, LeadSource, LeadStatus
from app.db.session import get_db
from app.models.user import User
from app.schemas.lead import LeadCreate, LeadListItem, LeadRead, LeadUpdate
from app.schemas.pagination import Page
from app.schemas.pipeline import LeadPipelineRead, LeadPipelineUpdate
from app.services.authorization_service import CompanyAccess
from app.services.lead_service import create_lead, get_lead, list_leads, update_lead
from app.services.pipeline_service import move_lead

router = APIRouter(prefix="/companies/{company_id}/leads", tags=["leads"])


@router.get("", response_model=Page[LeadListItem])
def lead_list(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=100),
    status: LeadStatus | None = None,
    source: LeadSource | None = None,
    priority: LeadPriority | None = None,
    campaign_id: UUID | None = None,
    assigned_to: UUID | None = None,
    created_from: date | None = None,
    created_to: date | None = None,
    db: Session = Depends(get_db),
    access: CompanyAccess = Depends(require_crm_writer),
) -> Page[LeadListItem]:
    return list_leads(
        db,
        access.company.id,
        page=page,
        page_size=page_size,
        search=search,
        status=status,
        source=source,
        priority=priority,
        campaign_id=campaign_id,
        assigned_to=assigned_to,
        created_from=created_from,
        created_to=created_to,
    )


@router.post("", response_model=LeadRead, status_code=201)
def lead_create(
    body: LeadCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
    access: CompanyAccess = Depends(require_crm_writer),
) -> LeadRead:
    return create_lead(db, actor.id, access.company.id, body)


@router.get("/{lead_id}", response_model=LeadRead)
def lead_detail(
    lead_id: UUID,
    db: Session = Depends(get_db),
    access: CompanyAccess = Depends(require_crm_writer),
) -> LeadRead:
    return get_lead(db, access.company.id, lead_id)


@router.patch("/{lead_id}/pipeline", response_model=LeadPipelineRead)
def lead_pipeline_move(
    lead_id: UUID,
    body: LeadPipelineUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
    access: CompanyAccess = Depends(require_crm_writer),
) -> LeadPipelineRead:
    return move_lead(db, actor.id, access.company.id, lead_id, body)


@router.patch("/{lead_id}", response_model=LeadRead)
def lead_update(
    lead_id: UUID,
    body: LeadUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
    access: CompanyAccess = Depends(require_crm_writer),
) -> LeadRead:
    return update_lead(db, actor.id, access.company.id, lead_id, body)

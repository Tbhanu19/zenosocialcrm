"""Company-scoped lead metrics types."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_crm_writer
from app.db.session import get_db
from app.models.user import User
from app.schemas.lead_metrics_type import (
    LeadMetricsTypeCreate,
    LeadMetricsTypeRead,
    LeadMetricsTypeUpdate,
)
from app.services.authorization_service import CompanyAccess
from app.services.lead_metrics_type_service import (
    create_lead_metrics_type,
    list_lead_metrics_types,
    update_lead_metrics_type,
)

router = APIRouter(
    prefix="/companies/{company_id}/lead-metrics-types",
    tags=["lead-metrics-types"],
)


@router.get("", response_model=list[LeadMetricsTypeRead])
def list_types(
    db: Session = Depends(get_db),
    access: CompanyAccess = Depends(require_crm_writer),
) -> list[LeadMetricsTypeRead]:
    return list_lead_metrics_types(db, access.company.id)


@router.post("", response_model=LeadMetricsTypeRead, status_code=201)
def create_type(
    body: LeadMetricsTypeCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
    access: CompanyAccess = Depends(require_crm_writer),
) -> LeadMetricsTypeRead:
    return create_lead_metrics_type(db, actor, access.company.id, body)


@router.patch("/{type_id}", response_model=LeadMetricsTypeRead)
def update_type(
    type_id: UUID,
    body: LeadMetricsTypeUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
    access: CompanyAccess = Depends(require_crm_writer),
) -> LeadMetricsTypeRead:
    return update_lead_metrics_type(db, actor, access.company.id, type_id, body)

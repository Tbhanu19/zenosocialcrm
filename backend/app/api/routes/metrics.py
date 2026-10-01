"""Company-scoped lead metrics."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_crm_writer
from app.core.permissions import LeadSource, LeadStatus
from app.db.session import get_db
from app.schemas.metrics import LeadMetrics
from app.services.authorization_service import CompanyAccess
from app.services.metrics_service import lead_metrics

router = APIRouter(prefix="/companies/{company_id}/lead-metrics", tags=["lead-metrics"])


@router.get("", response_model=LeadMetrics)
def lead_metrics_view(
    date_from: date | None = None,
    date_to: date | None = None,
    source: LeadSource | None = None,
    campaign_id: UUID | None = None,
    assigned_to_user_id: UUID | None = None,
    status: LeadStatus | None = None,
    db: Session = Depends(get_db),
    access: CompanyAccess = Depends(require_crm_writer),
) -> LeadMetrics:
    return lead_metrics(
        db,
        access.company.id,
        date_from=date_from,
        date_to=date_to,
        source=source,
        campaign_id=campaign_id,
        assigned_to_user_id=assigned_to_user_id,
        status=status,
    )

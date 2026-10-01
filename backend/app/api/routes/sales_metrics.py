"""Company-scoped sales metrics."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_user_manager
from app.core.permissions import LeadSource
from app.db.session import get_db
from app.schemas.sales_metrics import SalesMetrics
from app.services.authorization_service import CompanyAccess
from app.services.sales_metrics_service import sales_metrics

router = APIRouter(prefix="/companies/{company_id}/sales-metrics", tags=["sales-metrics"])


@router.get("", response_model=SalesMetrics)
def sales_metrics_view(
    date_from: date | None = None,
    date_to: date | None = None,
    pipeline_id: UUID | None = None,
    stage_id: UUID | None = None,
    assigned_to_user_id: UUID | None = None,
    source: LeadSource | None = None,
    campaign_id: UUID | None = None,
    db: Session = Depends(get_db),
    access: CompanyAccess = Depends(require_user_manager),
) -> SalesMetrics:
    return sales_metrics(
        db,
        access.company.id,
        date_from=date_from,
        date_to=date_to,
        pipeline_id=pipeline_id,
        stage_id=stage_id,
        assigned_to_user_id=assigned_to_user_id,
        source=source,
        campaign_id=campaign_id,
    )

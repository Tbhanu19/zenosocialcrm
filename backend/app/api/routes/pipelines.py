"""Company-scoped sales pipelines."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_crm_writer, require_user_manager
from app.core.permissions import LeadSource, PipelineStatus
from app.db.session import get_db
from app.models.user import User
from app.schemas.pagination import Page
from app.schemas.pipeline import (
    PipelineBoard,
    PipelineCard,
    PipelineCreate,
    PipelineListItem,
    PipelineRead,
    PipelineUpdate,
    StageCreate,
    StageRead,
    StageReorder,
    StageUpdate,
)
from app.services.authorization_service import CompanyAccess
from app.services.pipeline_service import (
    create_pipeline,
    create_stage,
    get_pipeline,
    list_pipelines,
    pipeline_board,
    reorder_stages,
    stage_leads,
    update_pipeline,
    update_stage,
)

router = APIRouter(prefix="/companies/{company_id}/sales-pipelines", tags=["sales-pipelines"])


@router.get("", response_model=Page[PipelineListItem])
def pipeline_list(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: PipelineStatus | None = None,
    db: Session = Depends(get_db),
    access: CompanyAccess = Depends(require_crm_writer),
) -> Page[PipelineListItem]:
    return list_pipelines(
        db,
        access.company.id,
        page=page,
        page_size=page_size,
        status=status,
    )


@router.post("", response_model=PipelineRead, status_code=201)
def pipeline_create(
    body: PipelineCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
    access: CompanyAccess = Depends(require_user_manager),
) -> PipelineRead:
    return create_pipeline(db, actor.id, access.company.id, body)


@router.get("/{pipeline_id}", response_model=PipelineRead)
def pipeline_detail(
    pipeline_id: UUID,
    db: Session = Depends(get_db),
    access: CompanyAccess = Depends(require_crm_writer),
) -> PipelineRead:
    return get_pipeline(db, access.company.id, pipeline_id)


@router.patch("/{pipeline_id}", response_model=PipelineRead)
def pipeline_update(
    pipeline_id: UUID,
    body: PipelineUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
    access: CompanyAccess = Depends(require_user_manager),
) -> PipelineRead:
    return update_pipeline(db, actor.id, access.company.id, pipeline_id, body)


@router.get("/{pipeline_id}/stages", response_model=list[StageRead])
def stage_list(
    pipeline_id: UUID,
    db: Session = Depends(get_db),
    access: CompanyAccess = Depends(require_crm_writer),
) -> list[StageRead]:
    return get_pipeline(db, access.company.id, pipeline_id).stages


@router.get("/{pipeline_id}/board", response_model=PipelineBoard)
def pipeline_board_view(
    pipeline_id: UUID,
    per_stage: int = Query(default=20, ge=1, le=50),
    search: str | None = Query(default=None, max_length=100),
    source: LeadSource | None = None,
    campaign_id: UUID | None = None,
    assigned_to: UUID | None = None,
    close_from: date | None = None,
    close_to: date | None = None,
    db: Session = Depends(get_db),
    access: CompanyAccess = Depends(require_crm_writer),
) -> PipelineBoard:
    return pipeline_board(
        db,
        access.company.id,
        pipeline_id,
        per_stage=per_stage,
        search=search,
        source=source,
        campaign_id=campaign_id,
        assigned_to=assigned_to,
        close_from=close_from,
        close_to=close_to,
    )


@router.get("/{pipeline_id}/stages/{stage_id}/leads", response_model=Page[PipelineCard])
def pipeline_stage_leads(
    pipeline_id: UUID,
    stage_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    search: str | None = Query(default=None, max_length=100),
    source: LeadSource | None = None,
    campaign_id: UUID | None = None,
    assigned_to: UUID | None = None,
    close_from: date | None = None,
    close_to: date | None = None,
    db: Session = Depends(get_db),
    access: CompanyAccess = Depends(require_crm_writer),
) -> Page[PipelineCard]:
    return stage_leads(
        db,
        access.company.id,
        pipeline_id,
        stage_id,
        page=page,
        page_size=page_size,
        search=search,
        source=source,
        campaign_id=campaign_id,
        assigned_to=assigned_to,
        close_from=close_from,
        close_to=close_to,
    )


@router.post("/{pipeline_id}/stages", response_model=StageRead, status_code=201)
def stage_create(
    pipeline_id: UUID,
    body: StageCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
    access: CompanyAccess = Depends(require_user_manager),
) -> StageRead:
    return create_stage(db, actor.id, access.company.id, pipeline_id, body)


@router.patch("/{pipeline_id}/stages/reorder", response_model=list[StageRead])
def stage_reorder(
    pipeline_id: UUID,
    body: StageReorder,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
    access: CompanyAccess = Depends(require_user_manager),
) -> list[StageRead]:
    return reorder_stages(db, actor.id, access.company.id, pipeline_id, body)


@router.patch("/{pipeline_id}/stages/{stage_id}", response_model=StageRead)
def stage_update(
    pipeline_id: UUID,
    stage_id: UUID,
    body: StageUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
    access: CompanyAccess = Depends(require_user_manager),
) -> StageRead:
    return update_stage(db, actor.id, access.company.id, pipeline_id, stage_id, body)

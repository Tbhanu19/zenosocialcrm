"""Company-scoped sales pipelines, stages, and the bounded board."""

import logging
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, aliased
from sqlalchemy.sql import Select
from sqlalchemy.sql.elements import ColumnElement

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.permissions import (
    LeadSource,
    LeadStatus,
    PipelineStatus,
    PreferredContactType,
    StageColor,
    StageStatus,
)
from app.core.search import contains_pattern
from app.models.contact import Contact
from app.models.lead import Lead
from app.models.pipeline import SalesPipeline
from app.models.pipeline_stage import SalesPipelineStage
from app.models.user import User
from app.schemas.pagination import Page, total_pages
from app.schemas.pipeline import (
    LeadPipelineRead,
    LeadPipelineUpdate,
    PipelineBoard,
    PipelineCard,
    PipelineCreate,
    PipelineListItem,
    PipelineRead,
    PipelineUpdate,
    StageColumn,
    StageCreate,
    StageRead,
    StageReorder,
    StageUpdate,
)
from app.services.campaign_service import money_text

logger = logging.getLogger("zenosocialcrm.pipeline")


def list_pipelines(
    db: Session,
    company_id: UUID,
    *,
    page: int,
    page_size: int,
    status: PipelineStatus | None,
) -> Page[PipelineListItem]:
    filters: list[ColumnElement[bool]] = [SalesPipeline.company_id == company_id]
    if status is None:
        filters.append(SalesPipeline.status != PipelineStatus.ARCHIVED.value)
    else:
        filters.append(SalesPipeline.status == status.value)
    total = db.scalar(select(func.count()).select_from(SalesPipeline).where(*filters)) or 0
    rows = db.scalars(
        select(SalesPipeline)
        .where(*filters)
        .order_by(SalesPipeline.created_at.desc(), SalesPipeline.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page(
        items=[
            PipelineListItem(
                id=row.id,
                name=row.name,
                status=PipelineStatus(row.status),
                created_at=row.created_at,
            )
            for row in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages(total, page_size),
    )


def get_pipeline(db: Session, company_id: UUID, pipeline_id: UUID) -> PipelineRead:
    pipeline = _pipeline_in_company(db, company_id, pipeline_id)
    stages = db.scalars(
        select(SalesPipelineStage)
        .where(SalesPipelineStage.pipeline_id == pipeline.id)
        .order_by(SalesPipelineStage.position.asc(), SalesPipelineStage.id.asc())
    ).all()
    listed = PipelineListItem(
        id=pipeline.id,
        name=pipeline.name,
        status=PipelineStatus(pipeline.status),
        created_at=pipeline.created_at,
    )
    return PipelineRead(
        **listed.model_dump(),
        description=pipeline.description,
        updated_at=pipeline.updated_at,
        stages=[_stage_read(stage) for stage in stages],
    )


def create_pipeline(
    db: Session,
    actor_id: UUID,
    company_id: UUID,
    data: PipelineCreate,
) -> PipelineRead:
    pipeline = SalesPipeline(
        company_id=company_id,
        name=data.name,
        description=data.description,
        status=data.status.value,
    )
    db.add(pipeline)
    db.commit()
    logger.info(
        "pipeline created actor_id=%s company_id=%s pipeline_id=%s",
        actor_id,
        company_id,
        pipeline.id,
    )
    return get_pipeline(db, company_id, pipeline.id)


def update_pipeline(
    db: Session,
    actor_id: UUID,
    company_id: UUID,
    pipeline_id: UUID,
    data: PipelineUpdate,
) -> PipelineRead:
    if not data.model_fields_set:
        raise BadRequestError("At least one field is required.")
    pipeline = _pipeline_in_company(db, company_id, pipeline_id)
    try:
        for field in data.model_fields_set:
            value = getattr(data, field)
            if field in {"name", "status"} and value is None:
                raise BadRequestError("Name and status cannot be cleared.")
            if field == "status":
                value = value.value
            setattr(pipeline, field, value)
    except BadRequestError:
        db.rollback()
        raise
    db.commit()
    logger.info(
        "pipeline updated actor_id=%s company_id=%s pipeline_id=%s",
        actor_id,
        company_id,
        pipeline.id,
    )
    return get_pipeline(db, company_id, pipeline.id)


def create_stage(
    db: Session,
    actor_id: UUID,
    company_id: UUID,
    pipeline_id: UUID,
    data: StageCreate,
) -> StageRead:
    pipeline = _pipeline_in_company(db, company_id, pipeline_id)
    current = db.scalar(
        select(func.max(SalesPipelineStage.position)).where(
            SalesPipelineStage.pipeline_id == pipeline.id
        )
    )
    stage = SalesPipelineStage(
        pipeline_id=pipeline.id,
        name=data.name,
        description=data.description,
        position=int(current or 0) + 1,
        color=data.color.value,
        status=data.status.value,
    )
    db.add(stage)
    db.commit()
    logger.info(
        "stage created actor_id=%s company_id=%s pipeline_id=%s stage_id=%s",
        actor_id,
        company_id,
        pipeline.id,
        stage.id,
    )
    return _stage_read(stage)


def update_stage(
    db: Session,
    actor_id: UUID,
    company_id: UUID,
    pipeline_id: UUID,
    stage_id: UUID,
    data: StageUpdate,
) -> StageRead:
    if not data.model_fields_set:
        raise BadRequestError("At least one field is required.")
    _pipeline_in_company(db, company_id, pipeline_id)
    stage = _stage_in_pipeline(db, pipeline_id, stage_id)
    if data.status is StageStatus.INACTIVE and _stage_lead_count(db, company_id, stage.id) > 0:
        raise ConflictError("Move leads to another stage before deactivating this one.")
    try:
        for field in data.model_fields_set:
            value = getattr(data, field)
            if field in {"name", "color", "status"} and value is None:
                raise BadRequestError("Name, color, and status cannot be cleared.")
            if field in {"color", "status"}:
                value = value.value
            setattr(stage, field, value)
    except BadRequestError:
        db.rollback()
        raise
    db.commit()
    logger.info(
        "stage updated actor_id=%s company_id=%s stage_id=%s",
        actor_id,
        company_id,
        stage.id,
    )
    return _stage_read(stage)


def reorder_stages(
    db: Session,
    actor_id: UUID,
    company_id: UUID,
    pipeline_id: UUID,
    data: StageReorder,
) -> list[StageRead]:
    pipeline = _pipeline_in_company(db, company_id, pipeline_id)
    stages = db.scalars(
        select(SalesPipelineStage).where(SalesPipelineStage.pipeline_id == pipeline.id)
    ).all()
    by_id = {stage.id: stage for stage in stages}
    if len(data.stage_ids) != len(set(data.stage_ids)) or set(data.stage_ids) != set(by_id):
        raise BadRequestError("Include every stage in this pipeline exactly once.")
    for index, stage_id in enumerate(data.stage_ids, start=1):
        by_id[stage_id].position = 1000 + index
    db.flush()
    for index, stage_id in enumerate(data.stage_ids, start=1):
        by_id[stage_id].position = index
    db.commit()
    logger.info(
        "stages reordered actor_id=%s company_id=%s pipeline_id=%s",
        actor_id,
        company_id,
        pipeline.id,
    )
    ordered = sorted(stages, key=lambda stage: (stage.position, str(stage.id)))
    return [_stage_read(stage) for stage in ordered]


def move_lead(
    db: Session,
    actor_id: UUID,
    company_id: UUID,
    lead_id: UUID,
    data: LeadPipelineUpdate,
) -> LeadPipelineRead:
    lead = db.scalar(select(Lead).where(Lead.company_id == company_id, Lead.id == lead_id))
    if lead is None:
        raise NotFoundError("Lead not found.")
    pipeline = _pipeline_in_company(db, company_id, data.pipeline_id)
    stage = _stage_in_pipeline(db, pipeline.id, data.pipeline_stage_id)
    if stage.status != StageStatus.ACTIVE.value:
        raise BadRequestError("Choose an active stage.")
    if (
        "expected_pipeline_stage_id" in data.model_fields_set
        and data.expected_pipeline_stage_id != lead.pipeline_stage_id
    ):
        raise ConflictError("This lead was moved by someone else. Refresh and try again.")
    lead.pipeline_id = pipeline.id
    lead.pipeline_stage_id = stage.id
    db.commit()
    logger.info(
        "lead moved actor_id=%s company_id=%s lead_id=%s stage_id=%s",
        actor_id,
        company_id,
        lead.id,
        stage.id,
    )
    return LeadPipelineRead(
        id=lead.id,
        title=lead.title,
        status=LeadStatus(lead.status),
        pipeline_id=pipeline.id,
        pipeline_stage_id=stage.id,
        pipeline_name=pipeline.name,
        stage_name=stage.name,
    )


def pipeline_board(
    db: Session,
    company_id: UUID,
    pipeline_id: UUID,
    *,
    per_stage: int,
    search: str | None,
    source: LeadSource | None,
    campaign_id: UUID | None,
    assigned_to: UUID | None,
    close_from: date | None,
    close_to: date | None,
) -> PipelineBoard:
    pipeline = _pipeline_in_company(db, company_id, pipeline_id)
    stages = db.scalars(
        select(SalesPipelineStage)
        .where(
            SalesPipelineStage.pipeline_id == pipeline.id,
            SalesPipelineStage.status == StageStatus.ACTIVE.value,
        )
        .order_by(SalesPipelineStage.position.asc(), SalesPipelineStage.id.asc())
    ).all()
    filters = _board_filters(
        company_id,
        pipeline.id,
        search,
        source,
        campaign_id,
        assigned_to,
        close_from,
        close_to,
    )
    totals_stmt = select(
        Lead.pipeline_stage_id,
        func.count(),
        func.coalesce(func.sum(Lead.estimated_value), 0),
    )
    if _needs_contact(search):
        totals_stmt = totals_stmt.outerjoin(Contact, Contact.id == Lead.contact_id)
    totals = {
        stage_id: (int(count), value)
        for stage_id, count, value in db.execute(
            totals_stmt.where(*filters).group_by(Lead.pipeline_stage_id)
        ).all()
    }
    cards = _stage_cards(db, filters, per_stage)
    columns: list[StageColumn] = []
    for stage in stages:
        count, value = totals.get(stage.id, (0, 0))
        stage_cards = cards.get(stage.id, [])
        columns.append(
            StageColumn(
                stage_id=stage.id,
                stage_name=stage.name,
                position=stage.position,
                color=StageColor(stage.color),
                lead_count=count,
                estimated_value_total=money_text(value) or "0.00",
                leads=stage_cards,
                has_more=count > len(stage_cards),
            )
        )
    return PipelineBoard(
        pipeline_id=pipeline.id,
        pipeline_name=pipeline.name,
        per_stage=per_stage,
        stages=columns,
    )


def stage_leads(
    db: Session,
    company_id: UUID,
    pipeline_id: UUID,
    stage_id: UUID,
    *,
    page: int,
    page_size: int,
    search: str | None,
    source: LeadSource | None,
    campaign_id: UUID | None,
    assigned_to: UUID | None,
    close_from: date | None,
    close_to: date | None,
) -> Page[PipelineCard]:
    _pipeline_in_company(db, company_id, pipeline_id)
    _stage_in_pipeline(db, pipeline_id, stage_id)
    filters = _board_filters(
        company_id,
        pipeline_id,
        search,
        source,
        campaign_id,
        assigned_to,
        close_from,
        close_to,
    )
    filters.append(Lead.pipeline_stage_id == stage_id)
    total = _count_cards(db, filters, search)
    rows = (
        _card_query(filters, search)
        .order_by(Lead.created_at.desc(), Lead.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return Page(
        items=[_card(row) for row in db.execute(rows).all()],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages(total, page_size),
    )


def _stage_cards(
    db: Session,
    filters: list[ColumnElement[bool]],
    per_stage: int,
) -> dict[UUID, list[PipelineCard]]:
    assignee = aliased(User)
    ranked = (
        select(
            Lead.id.label("id"),
            Lead.title.label("title"),
            Lead.source.label("source"),
            Lead.estimated_value.label("estimated_value"),
            Lead.expected_close_date.label("expected_close_date"),
            Lead.pipeline_stage_id.label("pipeline_stage_id"),
            Lead.preferred_contact_type.label("preferred_contact_type"),
            Lead.pipeline_created_at.label("pipeline_created_at"),
            Contact.first_name.label("contact_first"),
            Contact.last_name.label("contact_last"),
            assignee.first_name.label("assignee_first"),
            assignee.last_name.label("assignee_last"),
            func.row_number()
            .over(
                partition_by=Lead.pipeline_stage_id,
                order_by=(Lead.created_at.desc(), Lead.id.desc()),
            )
            .label("rn"),
        )
        .outerjoin(Contact, Contact.id == Lead.contact_id)
        .outerjoin(assignee, assignee.id == Lead.assigned_to_user_id)
        .where(*filters)
    ).subquery()
    rows = db.execute(select(ranked).where(ranked.c.rn <= per_stage)).all()
    grouped: dict[UUID, list[PipelineCard]] = {}
    for row in rows:
        grouped.setdefault(row.pipeline_stage_id, []).append(_card(row))
    return grouped


def _card_query(filters: list[ColumnElement[bool]], search: str | None) -> Select[Any]:
    del search
    assignee = aliased(User)
    return (
        select(
            Lead.id.label("id"),
            Lead.title.label("title"),
            Lead.source.label("source"),
            Lead.estimated_value.label("estimated_value"),
            Lead.expected_close_date.label("expected_close_date"),
            Lead.pipeline_stage_id.label("pipeline_stage_id"),
            Lead.preferred_contact_type.label("preferred_contact_type"),
            Lead.pipeline_created_at.label("pipeline_created_at"),
            Contact.first_name.label("contact_first"),
            Contact.last_name.label("contact_last"),
            assignee.first_name.label("assignee_first"),
            assignee.last_name.label("assignee_last"),
        )
        .outerjoin(Contact, Contact.id == Lead.contact_id)
        .outerjoin(assignee, assignee.id == Lead.assigned_to_user_id)
        .where(*filters)
    )


def _count_cards(db: Session, filters: list[ColumnElement[bool]], search: str | None) -> int:
    statement = select(func.count()).select_from(Lead)
    if _needs_contact(search):
        statement = statement.outerjoin(Contact, Contact.id == Lead.contact_id)
    return int(db.scalar(statement.where(*filters)) or 0)


def _card(row: object) -> PipelineCard:
    values = row._mapping  # type: ignore[attr-defined]
    return PipelineCard(
        id=values["id"],
        title=values["title"],
        contact_name=_person(values["contact_first"], values["contact_last"]),
        estimated_value=money_text(values["estimated_value"]),
        assignee_name=_person(values["assignee_first"], values["assignee_last"]),
        source=LeadSource(values["source"]),
        expected_close_date=values["expected_close_date"],
        pipeline_stage_id=values["pipeline_stage_id"],
        preferred_contact_type=(
            None
            if values["preferred_contact_type"] is None
            else PreferredContactType(values["preferred_contact_type"])
        ),
        pipeline_created_at=values["pipeline_created_at"],
    )


def _board_filters(
    company_id: UUID,
    pipeline_id: UUID,
    search: str | None,
    source: LeadSource | None,
    campaign_id: UUID | None,
    assigned_to: UUID | None,
    close_from: date | None,
    close_to: date | None,
) -> list[ColumnElement[bool]]:
    filters: list[ColumnElement[bool]] = [
        Lead.company_id == company_id,
        Lead.pipeline_id == pipeline_id,
        Lead.status != LeadStatus.ARCHIVED.value,
    ]
    if source is not None:
        filters.append(Lead.source == source.value)
    if campaign_id is not None:
        filters.append(Lead.campaign_id == campaign_id)
    if assigned_to is not None:
        filters.append(Lead.assigned_to_user_id == assigned_to)
    if close_from is not None:
        filters.append(Lead.expected_close_date >= close_from)
    if close_to is not None:
        filters.append(Lead.expected_close_date <= close_to)
    term = (search or "").strip()
    if term:
        pattern = contains_pattern(term)
        filters.append(
            or_(
                Lead.title.ilike(pattern, escape="\\"),
                Contact.first_name.ilike(pattern, escape="\\"),
                Contact.last_name.ilike(pattern, escape="\\"),
                Contact.email.ilike(pattern, escape="\\"),
            )
        )
    return filters


def _needs_contact(search: str | None) -> bool:
    return bool((search or "").strip())


def _pipeline_in_company(db: Session, company_id: UUID, pipeline_id: UUID) -> SalesPipeline:
    pipeline = db.scalar(
        select(SalesPipeline).where(
            SalesPipeline.company_id == company_id,
            SalesPipeline.id == pipeline_id,
        )
    )
    if pipeline is None:
        raise NotFoundError("Pipeline not found.")
    return pipeline


def _stage_in_pipeline(db: Session, pipeline_id: UUID, stage_id: UUID) -> SalesPipelineStage:
    stage = db.scalar(
        select(SalesPipelineStage).where(
            SalesPipelineStage.pipeline_id == pipeline_id,
            SalesPipelineStage.id == stage_id,
        )
    )
    if stage is None:
        raise NotFoundError("Stage not found.")
    return stage


def _stage_lead_count(db: Session, company_id: UUID, stage_id: UUID) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(Lead)
            .where(Lead.company_id == company_id, Lead.pipeline_stage_id == stage_id)
        )
        or 0
    )


def _stage_read(stage: SalesPipelineStage) -> StageRead:
    return StageRead(
        id=stage.id,
        pipeline_id=stage.pipeline_id,
        name=stage.name,
        description=stage.description,
        position=stage.position,
        color=StageColor(stage.color),
        status=StageStatus(stage.status),
    )


def _person(first_name: str | None, last_name: str | None) -> str | None:
    if first_name is None or last_name is None:
        return None
    return f"{first_name} {last_name}"

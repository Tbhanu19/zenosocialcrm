"""Lead metrics types for a company."""

import logging
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.core.permissions import CompanyStatus
from app.models.lead_metrics_type import LeadMetricsType
from app.models.user import User
from app.schemas.lead_metrics_type import (
    LeadMetricsTypeCreate,
    LeadMetricsTypeRead,
    LeadMetricsTypeUpdate,
)

logger = logging.getLogger("zenosocialcrm.lead_metrics_types")


def list_lead_metrics_types(db: Session, company_id: UUID) -> list[LeadMetricsTypeRead]:
    rows = db.scalars(
        select(LeadMetricsType)
        .where(LeadMetricsType.company_id == company_id)
        .order_by(LeadMetricsType.name.asc(), LeadMetricsType.id.asc())
    ).all()
    return [_read(row) for row in rows]


def create_lead_metrics_type(
    db: Session,
    actor: User,
    company_id: UUID,
    data: LeadMetricsTypeCreate,
) -> LeadMetricsTypeRead:
    _ensure_unique_name(db, company_id, data.name)
    row = LeadMetricsType(
        company_id=company_id,
        name=data.name,
        description=data.description,
        value=data.value,
        status=data.status.value,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    logger.info(
        "lead metrics type created actor_id=%s company_id=%s type_id=%s",
        actor.id,
        company_id,
        row.id,
    )
    return _read(row)


def update_lead_metrics_type(
    db: Session,
    actor: User,
    company_id: UUID,
    type_id: UUID,
    data: LeadMetricsTypeUpdate,
) -> LeadMetricsTypeRead:
    row = db.scalar(
        select(LeadMetricsType).where(
            LeadMetricsType.id == type_id,
            LeadMetricsType.company_id == company_id,
        )
    )
    if row is None:
        raise NotFoundError("Lead metrics type not found.")
    changes = data.model_dump(exclude_unset=True)
    if "name" in changes and changes["name"] is not None:
        _ensure_unique_name(db, company_id, changes["name"], exclude_id=row.id)
        row.name = changes["name"]
    if "description" in changes:
        row.description = changes["description"]
    if "value" in changes and changes["value"] is not None:
        row.value = changes["value"]
    if "status" in changes and changes["status"] is not None:
        status = changes["status"]
        row.status = status.value if isinstance(status, CompanyStatus) else status
    db.commit()
    db.refresh(row)
    logger.info(
        "lead metrics type updated actor_id=%s company_id=%s type_id=%s",
        actor.id,
        company_id,
        row.id,
    )
    return _read(row)


def _ensure_unique_name(
    db: Session,
    company_id: UUID,
    name: str,
    exclude_id: UUID | None = None,
) -> None:
    query = select(LeadMetricsType.id).where(
        LeadMetricsType.company_id == company_id,
        func.lower(LeadMetricsType.name) == name.lower(),
    )
    if exclude_id is not None:
        query = query.where(LeadMetricsType.id != exclude_id)
    if db.scalar(query) is not None:
        raise ConflictError("A lead metrics type with this name already exists.")


def _read(row: LeadMetricsType) -> LeadMetricsTypeRead:
    return LeadMetricsTypeRead(
        id=row.id,
        company_id=row.company_id,
        name=row.name,
        description=row.description,
        value=row.value,
        status=CompanyStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )

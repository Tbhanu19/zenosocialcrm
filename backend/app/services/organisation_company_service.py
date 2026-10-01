"""Nested companies inside an organisation."""

import logging
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.core.permissions import CompanyStatus
from app.models.company import Company
from app.models.organisation_company import OrganisationCompany
from app.models.user import User
from app.schemas.organisation_company import OrganisationCompanyCreate, OrganisationCompanyRead

logger = logging.getLogger("zenosocialcrm.organisation_companies")


def list_organisation_companies(db: Session, organisation_id: UUID) -> list[OrganisationCompanyRead]:
    _require_organisation(db, organisation_id)
    rows = db.scalars(
        select(OrganisationCompany)
        .where(OrganisationCompany.organisation_id == organisation_id)
        .order_by(OrganisationCompany.name.asc(), OrganisationCompany.id.asc())
    ).all()
    return [_read(row) for row in rows]


def create_organisation_company(
    db: Session,
    actor: User,
    organisation_id: UUID,
    data: OrganisationCompanyCreate,
) -> OrganisationCompanyRead:
    _require_organisation(db, organisation_id)
    existing = db.scalar(
        select(OrganisationCompany.id).where(
            OrganisationCompany.organisation_id == organisation_id,
            func.lower(OrganisationCompany.name) == data.name.lower(),
        )
    )
    if existing is not None:
        raise ConflictError("A company with this name already exists in this organisation.")
    row = OrganisationCompany(
        organisation_id=organisation_id,
        name=data.name,
        business_type=data.business_type,
        phone=data.phone,
        email=data.email,
        status=data.status.value,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    logger.info(
        "organisation company created actor_id=%s organisation_id=%s company_id=%s",
        actor.id,
        organisation_id,
        row.id,
    )
    return _read(row)


def _require_organisation(db: Session, organisation_id: UUID) -> Company:
    company = db.get(Company, organisation_id)
    if company is None:
        raise NotFoundError("Organisation not found.")
    return company


def _read(row: OrganisationCompany) -> OrganisationCompanyRead:
    return OrganisationCompanyRead(
        id=row.id,
        organisation_id=row.organisation_id,
        name=row.name,
        business_type=row.business_type,
        phone=row.phone,
        email=row.email,
        status=CompanyStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )

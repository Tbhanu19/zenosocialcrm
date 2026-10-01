"""Company access endpoints. Responses include only authorized companies."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_company_access, require_crm_writer
from app.db.session import get_db
from app.models.user import User
from app.schemas.company import AvailableCompanyRead, CompanyAccessRead, CompanyRead
from app.schemas.organisation_company import OrganisationCompanyRead
from app.services.authorization_service import CompanyAccess, list_accessible_companies
from app.services.organisation_company_service import list_organisation_companies

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("/available", response_model=list[AvailableCompanyRead])
def available_companies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AvailableCompanyRead]:
    return list_accessible_companies(db, current_user)


@router.get("/{company_id}/organisation-companies", response_model=list[OrganisationCompanyRead])
def organisation_companies_for_tenant(
    company_id: UUID,
    db: Session = Depends(get_db),
    _: CompanyAccess = Depends(require_crm_writer),
) -> list[OrganisationCompanyRead]:
    return list_organisation_companies(db, company_id)


@router.get("/{company_id}", response_model=CompanyAccessRead)
def get_company(access: CompanyAccess = Depends(require_company_access)) -> CompanyAccessRead:
    payload = CompanyRead.model_validate(access.company).model_dump()
    return CompanyAccessRead(**payload, role=access.role)

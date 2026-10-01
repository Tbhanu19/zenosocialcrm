"""Super-admin company administration."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import require_super_admin
from app.core.exceptions import NotFoundError
from app.core.permissions import CompanyStatus
from app.db.session import get_db
from app.models.company import Company
from app.models.user import User
from app.schemas.company import (
    AdminCompanyCreate,
    AdminCompanyCreated,
    AdminCompanyDetail,
    AdminCompanyListItem,
    CompanyRead,
    CompanyUpdate,
)
from app.schemas.organisation_company import OrganisationCompanyCreate, OrganisationCompanyRead
from app.schemas.pagination import Page
from app.services.company_admin_service import (
    create_company_with_owner,
    delete_company,
    get_company_detail,
    list_companies,
    update_company,
)
from app.services.organisation_company_service import (
    create_organisation_company,
    list_organisation_companies,
)

router = APIRouter(prefix="/admin/companies", tags=["admin-companies"])


@router.get("", response_model=Page[AdminCompanyListItem])
def admin_company_list(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=100),
    status: CompanyStatus | None = None,
    business_type: str | None = Query(default=None, max_length=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
) -> Page[AdminCompanyListItem]:
    return list_companies(
        db,
        page=page,
        page_size=page_size,
        search=search,
        status=status,
        business_type=business_type,
    )


@router.post("", response_model=AdminCompanyCreated, status_code=201)
def admin_create_company(
    body: AdminCompanyCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_super_admin),
) -> AdminCompanyCreated:
    return create_company_with_owner(db, actor, body)


@router.get("/{company_id}", response_model=AdminCompanyDetail)
def admin_company_detail(
    company_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
) -> AdminCompanyDetail:
    company = db.get(Company, company_id)
    if company is None:
        raise NotFoundError("Company not found.")
    return get_company_detail(db, company)


@router.patch("/{company_id}", response_model=CompanyRead)
def admin_update_company(
    company_id: UUID,
    body: CompanyUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_super_admin),
) -> Company:
    company = db.get(Company, company_id)
    if company is None:
        raise NotFoundError("Company not found.")
    return update_company(db, actor, company, body)


@router.delete("/{company_id}", status_code=204)
def admin_delete_company(
    company_id: UUID,
    db: Session = Depends(get_db),
    actor: User = Depends(require_super_admin),
) -> Response:
    company = db.get(Company, company_id)
    if company is None:
        raise NotFoundError("Organisation not found.")
    delete_company(db, actor, company)
    return Response(status_code=204)


@router.get("/{company_id}/companies", response_model=list[OrganisationCompanyRead])
def admin_organisation_companies(
    company_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
) -> list[OrganisationCompanyRead]:
    return list_organisation_companies(db, company_id)


@router.post("/{company_id}/companies", response_model=OrganisationCompanyRead, status_code=201)
def admin_create_organisation_company(
    company_id: UUID,
    body: OrganisationCompanyCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_super_admin),
) -> OrganisationCompanyRead:
    return create_organisation_company(db, actor, company_id, body)

"""Company-scoped contact routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_company_access, require_crm_writer
from app.core.permissions import ContactSource, ContactStatus
from app.db.session import get_db
from app.models.user import User
from app.schemas.contact import (
    AssigneeOption,
    ContactCreate,
    ContactListItem,
    ContactRead,
    ContactUpdate,
)
from app.schemas.pagination import Page
from app.services.authorization_service import CompanyAccess
from app.services.contact_service import (
    create_contact,
    delete_contact,
    get_contact,
    list_assignees,
    list_contacts,
    update_contact,
)

router = APIRouter(prefix="/companies/{company_id}/contacts", tags=["contacts"])


@router.get("", response_model=Page[ContactListItem])
def contact_list(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=100),
    status: ContactStatus | None = None,
    source: ContactSource | None = None,
    assigned_to: UUID | None = None,
    db: Session = Depends(get_db),
    access: CompanyAccess = Depends(require_company_access),
) -> Page[ContactListItem]:
    return list_contacts(
        db,
        access.company.id,
        page=page,
        page_size=page_size,
        search=search,
        status=status,
        source=source,
        assigned_to=assigned_to,
    )


@router.get("/assignees", response_model=Page[AssigneeOption])
def contact_assignees(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    access: CompanyAccess = Depends(require_company_access),
) -> Page[AssigneeOption]:
    return list_assignees(db, access.company.id, page=page, page_size=page_size)


@router.post("", response_model=ContactRead, status_code=201)
def contact_create(
    body: ContactCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
    access: CompanyAccess = Depends(require_crm_writer),
) -> ContactRead:
    return create_contact(db, actor.id, access.company.id, body)


@router.get("/{contact_id}", response_model=ContactRead)
def contact_detail(
    contact_id: UUID,
    db: Session = Depends(get_db),
    access: CompanyAccess = Depends(require_company_access),
) -> ContactRead:
    return get_contact(db, access.company.id, contact_id)


@router.patch("/{contact_id}", response_model=ContactRead)
def contact_update(
    contact_id: UUID,
    body: ContactUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
    access: CompanyAccess = Depends(require_crm_writer),
) -> ContactRead:
    return update_contact(db, actor.id, access.company.id, contact_id, body)


@router.delete("/{contact_id}", status_code=204)
def contact_delete(
    contact_id: UUID,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
    access: CompanyAccess = Depends(require_crm_writer),
) -> None:
    delete_contact(db, actor.id, access.company.id, contact_id)

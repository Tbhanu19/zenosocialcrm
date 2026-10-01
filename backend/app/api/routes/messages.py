"""Company-scoped message routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_company_access
from app.core.permissions import MessageStatus, MessageType
from app.db.session import get_db
from app.models.user import User
from app.schemas.message import (
    MessageCreate,
    MessageCreated,
    MessageListItem,
    MessageRead,
    MessageUpdate,
)
from app.schemas.pagination import Page
from app.services.authorization_service import CompanyAccess
from app.services.message_service import (
    create_message,
    get_message,
    list_messages,
    update_message,
)

router = APIRouter(prefix="/companies/{company_id}/messages", tags=["messages"])


@router.get("", response_model=Page[MessageListItem])
def message_list(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=100),
    message_type: MessageType | None = None,
    status: MessageStatus | None = None,
    contact_id: UUID | None = None,
    db: Session = Depends(get_db),
    access: CompanyAccess = Depends(require_company_access),
) -> Page[MessageListItem]:
    return list_messages(
        db,
        access.company.id,
        page=page,
        page_size=page_size,
        search=search,
        message_type=message_type,
        status=status,
        contact_id=contact_id,
    )


@router.post("", response_model=MessageCreated, status_code=201)
def message_create(
    body: MessageCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
    access: CompanyAccess = Depends(require_company_access),
) -> MessageCreated:
    message, provider_status = create_message(db, actor.id, access.company.id, body)
    return MessageCreated(message=message, provider_status=provider_status)


@router.get("/{message_id}", response_model=MessageRead)
def message_detail(
    message_id: UUID,
    db: Session = Depends(get_db),
    access: CompanyAccess = Depends(require_company_access),
) -> MessageRead:
    return get_message(db, access.company.id, message_id)


@router.patch("/{message_id}", response_model=MessageRead)
def message_update(
    message_id: UUID,
    body: MessageUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
    access: CompanyAccess = Depends(require_company_access),
) -> MessageRead:
    return update_message(db, actor.id, access.company.id, message_id, body)

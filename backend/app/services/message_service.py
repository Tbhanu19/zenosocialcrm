"""Company-scoped messages.

Contact and creator names are joined into the list query. Nothing here marks a
message sent or delivered unless a delivery provider returns an id.
"""

import logging
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.core.exceptions import BadRequestError, NotFoundError
from app.core.permissions import (
    ContactStatus,
    MessageDirection,
    MessageStatus,
    MessageType,
)
from app.core.search import contains_pattern
from app.models.contact import Contact
from app.models.message import Message
from app.models.user import User
from app.schemas.message import MessageCreate, MessageListItem, MessageRead, MessageUpdate
from app.schemas.pagination import Page, total_pages
from app.services.delivery import ProviderUnavailable, get_delivery_gateway

logger = logging.getLogger("zenosocialcrm.messages")

_PROVIDER_UNAVAILABLE = "No email or SMS provider is configured."


def list_messages(
    db: Session,
    company_id: UUID,
    *,
    page: int,
    page_size: int,
    search: str | None,
    message_type: MessageType | None,
    status: MessageStatus | None,
    contact_id: UUID | None,
) -> Page[MessageListItem]:
    filters = _message_filters(company_id, search, message_type, status, contact_id)
    count_stmt = select(func.count()).select_from(Message)
    if _needs_contact_join(search):
        count_stmt = count_stmt.outerjoin(Contact, Contact.id == Message.contact_id)
    total = db.scalar(count_stmt.where(*filters)) or 0
    rows = db.execute(
        select(
            Message,
            Contact.first_name,
            Contact.last_name,
            User.first_name,
            User.last_name,
        )
        .outerjoin(Contact, Contact.id == Message.contact_id)
        .outerjoin(User, User.id == Message.created_by_user_id)
        .where(*filters)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items = [
        _list_item(message, contact_first, contact_last, creator_first, creator_last)
        for message, contact_first, contact_last, creator_first, creator_last in rows
    ]
    return Page(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages(total, page_size),
    )


def get_message(db: Session, company_id: UUID, message_id: UUID) -> MessageRead:
    row = db.execute(
        select(Message, Contact, User)
        .outerjoin(Contact, Contact.id == Message.contact_id)
        .outerjoin(User, User.id == Message.created_by_user_id)
        .where(Message.company_id == company_id, Message.id == message_id)
    ).one_or_none()
    if row is None:
        raise NotFoundError("Message not found.")
    message, contact, creator = row
    return _detail(message, contact, creator)


def create_message(
    db: Session,
    actor_id: UUID,
    company_id: UUID,
    data: MessageCreate,
) -> tuple[MessageRead, str]:
    contact = db.scalar(
        select(Contact).where(Contact.id == data.contact_id, Contact.company_id == company_id)
    )
    if contact is None:
        raise NotFoundError("Contact not found.")
    if contact.status == ContactStatus.ARCHIVED.value:
        raise BadRequestError("This contact is archived.")
    subject = _validated_content(data.message_type, data.subject, contact)
    provider_status = "draft"
    error_message: str | None = None
    status = MessageStatus.DRAFT
    provider_message_id: str | None = None
    if data.deliver:
        provider_status, status, provider_message_id, error_message = _deliver(
            data.message_type,
            contact,
            subject,
            data.body,
        )
    message = Message(
        company_id=company_id,
        contact_id=contact.id,
        created_by_user_id=actor_id,
        message_type=data.message_type.value,
        direction=MessageDirection.OUTBOUND.value,
        subject=subject,
        body=data.body,
        status=status.value,
        provider_message_id=provider_message_id,
        error_message=error_message,
    )
    db.add(message)
    db.commit()
    logger.info(
        "message created actor_id=%s company_id=%s message_id=%s provider_status=%s",
        actor_id,
        company_id,
        message.id,
        provider_status,
    )
    return get_message(db, company_id, message.id), provider_status


def update_message(
    db: Session,
    actor_id: UUID,
    company_id: UUID,
    message_id: UUID,
    data: MessageUpdate,
) -> MessageRead:
    if not data.model_fields_set:
        raise BadRequestError("At least one field is required.")
    message = db.scalar(
        select(Message).where(Message.company_id == company_id, Message.id == message_id)
    )
    if message is None:
        raise NotFoundError("Message not found.")
    if message.status != MessageStatus.DRAFT.value:
        raise BadRequestError("Only drafts can be edited.")
    if message.message_type == MessageType.EMAIL.value and "subject" in data.model_fields_set:
        if not data.subject:
            raise BadRequestError("Subject is required for email.")
        message.subject = data.subject
    if message.message_type == MessageType.SMS.value:
        message.subject = None
    if "body" in data.model_fields_set and data.body is not None:
        message.body = data.body
    db.commit()
    logger.info(
        "message updated actor_id=%s company_id=%s message_id=%s",
        actor_id,
        company_id,
        message.id,
    )
    return get_message(db, company_id, message.id)


def _deliver(
    message_type: MessageType,
    contact: Contact,
    subject: str | None,
    body: str,
) -> tuple[str, MessageStatus, str | None, str | None]:
    gateway = get_delivery_gateway()
    try:
        if message_type is MessageType.EMAIL:
            provider_message_id = gateway.send_email(
                to_address=contact.email or "",
                subject=subject or "",
                body=body,
            )
        else:
            provider_message_id = gateway.send_sms(to_number=contact.phone or "", body=body)
    except ProviderUnavailable:
        return "unavailable", MessageStatus.DRAFT, None, _PROVIDER_UNAVAILABLE
    return "queued", MessageStatus.QUEUED, provider_message_id, None


def _validated_content(
    message_type: MessageType,
    subject: str | None,
    contact: Contact,
) -> str | None:
    if message_type is MessageType.EMAIL:
        if not subject:
            raise BadRequestError("Subject is required for email.")
        if not contact.email:
            raise BadRequestError("This contact has no email address.")
        return subject
    if not contact.phone:
        raise BadRequestError("This contact has no phone number.")
    return None


def _message_filters(
    company_id: UUID,
    search: str | None,
    message_type: MessageType | None,
    status: MessageStatus | None,
    contact_id: UUID | None,
) -> list[ColumnElement[bool]]:
    filters: list[ColumnElement[bool]] = [Message.company_id == company_id]
    if message_type is not None:
        filters.append(Message.message_type == message_type.value)
    if status is not None:
        filters.append(Message.status == status.value)
    if contact_id is not None:
        filters.append(Message.contact_id == contact_id)
    term = (search or "").strip()
    if term:
        pattern = contains_pattern(term)
        filters.append(
            or_(
                Message.subject.ilike(pattern, escape="\\"),
                Message.body.ilike(pattern, escape="\\"),
                Contact.first_name.ilike(pattern, escape="\\"),
                Contact.last_name.ilike(pattern, escape="\\"),
                Contact.email.ilike(pattern, escape="\\"),
            )
        )
    return filters


def _needs_contact_join(search: str | None) -> bool:
    return bool((search or "").strip())


def _list_item(
    message: Message,
    contact_first: str | None,
    contact_last: str | None,
    creator_first: str | None,
    creator_last: str | None,
) -> MessageListItem:
    return MessageListItem(
        id=message.id,
        contact_id=message.contact_id,
        contact_name=_person_name(contact_first, contact_last),
        message_type=MessageType(message.message_type),
        direction=MessageDirection(message.direction),
        subject=message.subject,
        body=message.body,
        status=MessageStatus(message.status),
        created_by_user_id=message.created_by_user_id,
        creator_name=_person_name(creator_first, creator_last),
        created_at=message.created_at,
    )


def _detail(message: Message, contact: Contact | None, creator: User | None) -> MessageRead:
    listed = _list_item(
        message,
        None if contact is None else contact.first_name,
        None if contact is None else contact.last_name,
        None if creator is None else creator.first_name,
        None if creator is None else creator.last_name,
    )
    return MessageRead(
        **listed.model_dump(),
        contact_email=None if contact is None else contact.email,
        contact_phone=None if contact is None else contact.phone,
        provider=message.provider,
        provider_message_id=message.provider_message_id,
        error_message=message.error_message,
        sent_at=message.sent_at,
        updated_at=message.updated_at,
    )


def _person_name(first_name: str | None, last_name: str | None) -> str | None:
    if first_name is None or last_name is None:
        return None
    return f"{first_name} {last_name}"

"""Company-scoped contacts.

List and detail queries join the assignee in the same statement so a page of
contacts does not query the user table once per row.
"""

import logging
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.permissions import ContactSource, ContactStatus, MembershipStatus
from app.core.search import contains_pattern
from app.models.contact import Contact
from app.models.user import User
from app.models.user_company import UserCompany
from app.schemas.contact import (
    AssigneeOption,
    ContactCreate,
    ContactListItem,
    ContactRead,
    ContactUpdate,
)
from app.schemas.pagination import Page, total_pages

logger = logging.getLogger("zenosocialcrm.contacts")


def list_contacts(
    db: Session,
    company_id: UUID,
    *,
    page: int,
    page_size: int,
    search: str | None,
    status: ContactStatus | None,
    source: ContactSource | None,
    assigned_to: UUID | None,
) -> Page[ContactListItem]:
    filters = _contact_filters(company_id, search, status, source, assigned_to)
    total = db.scalar(select(func.count()).select_from(Contact).where(*filters)) or 0
    rows = db.execute(
        select(Contact, User.first_name, User.last_name)
        .outerjoin(User, User.id == Contact.assigned_to_user_id)
        .where(*filters)
        .order_by(Contact.created_at.desc(), Contact.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items = [
        _list_item(contact, first_name, last_name) for contact, first_name, last_name in rows
    ]
    return Page(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages(total, page_size),
    )


def list_assignees(
    db: Session,
    company_id: UUID,
    *,
    page: int,
    page_size: int,
) -> Page[AssigneeOption]:
    filters: tuple[ColumnElement[bool], ...] = (
        UserCompany.company_id == company_id,
        UserCompany.status == MembershipStatus.ACTIVE.value,
    )
    total = db.scalar(select(func.count()).select_from(UserCompany).where(*filters)) or 0
    rows = db.execute(
        select(User.id, User.first_name, User.last_name)
        .join(UserCompany, UserCompany.user_id == User.id)
        .where(*filters)
        .order_by(User.last_name, User.first_name, User.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page(
        items=[
            AssigneeOption(id=user_id, first_name=first_name, last_name=last_name)
            for user_id, first_name, last_name in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages(total, page_size),
    )


def get_contact(db: Session, company_id: UUID, contact_id: UUID) -> ContactRead:
    row = db.execute(
        select(Contact, User.first_name, User.last_name)
        .outerjoin(User, User.id == Contact.assigned_to_user_id)
        .where(Contact.company_id == company_id, Contact.id == contact_id)
    ).one_or_none()
    if row is None:
        raise NotFoundError("Contact not found.")
    contact, first_name, last_name = row
    return _detail(contact, first_name, last_name)


def create_contact(
    db: Session,
    actor_id: UUID,
    company_id: UUID,
    data: ContactCreate,
) -> ContactRead:
    _require_active_member(db, company_id, data.assigned_to_user_id)
    contact = Contact(
        company_id=company_id,
        first_name=data.first_name,
        last_name=data.last_name,
        email=data.email,
        phone=data.phone,
        company_name=data.company_name,
        address=data.address,
        city=data.city,
        state=data.state,
        zip_code=data.zip_code,
        source=data.source.value,
        status=data.status.value,
        opted_in=data.opted_in,
        contact_date=data.contact_date,
        notes=data.notes,
        assigned_to_user_id=data.assigned_to_user_id,
    )
    db.add(contact)
    _commit_contact(db)
    logger.info(
        "contact created actor_id=%s company_id=%s contact_id=%s",
        actor_id,
        company_id,
        contact.id,
    )
    return get_contact(db, company_id, contact.id)


def update_contact(
    db: Session,
    actor_id: UUID,
    company_id: UUID,
    contact_id: UUID,
    data: ContactUpdate,
) -> ContactRead:
    if not data.model_fields_set:
        raise BadRequestError("At least one field is required.")
    contact = db.scalar(
        select(Contact).where(Contact.company_id == company_id, Contact.id == contact_id)
    )
    if contact is None:
        raise NotFoundError("Contact not found.")
    if "assigned_to_user_id" in data.model_fields_set:
        _require_active_member(db, company_id, data.assigned_to_user_id)
    for field in data.model_fields_set:
        value = getattr(data, field)
        if field in {"first_name", "last_name", "status", "source"} and value is None:
            raise BadRequestError("Name, status, and source cannot be cleared.")
        if field in {"status", "source"}:
            value = value.value
        setattr(contact, field, value)
    _commit_contact(db)
    logger.info(
        "contact updated actor_id=%s company_id=%s contact_id=%s",
        actor_id,
        company_id,
        contact.id,
    )
    return get_contact(db, company_id, contact.id)


def delete_contact(
    db: Session,
    actor_id: UUID,
    company_id: UUID,
    contact_id: UUID,
) -> None:
    contact = db.scalar(
        select(Contact).where(Contact.company_id == company_id, Contact.id == contact_id)
    )
    if contact is None:
        raise NotFoundError("Contact not found.")
    from app.models.lead import Lead
    from app.models.message import Message

    has_messages = db.scalar(
        select(Message.id).where(Message.contact_id == contact_id).limit(1)
    )
    if has_messages is not None:
        raise ConflictError("Delete this contact's messages before deleting the contact.")
    has_leads = db.scalar(select(Lead.id).where(Lead.contact_id == contact_id).limit(1))
    if has_leads is not None:
        raise ConflictError("This contact is linked to leads and cannot be deleted.")
    db.delete(contact)
    db.commit()
    logger.info(
        "contact deleted actor_id=%s company_id=%s contact_id=%s",
        actor_id,
        company_id,
        contact_id,
    )


def _contact_filters(
    company_id: UUID,
    search: str | None,
    status: ContactStatus | None,
    source: ContactSource | None,
    assigned_to: UUID | None,
) -> list[ColumnElement[bool]]:
    filters: list[ColumnElement[bool]] = [Contact.company_id == company_id]
    if status is None:
        filters.append(Contact.status != ContactStatus.ARCHIVED.value)
    else:
        filters.append(Contact.status == status.value)
    if source is not None:
        filters.append(Contact.source == source.value)
    if assigned_to is not None:
        filters.append(Contact.assigned_to_user_id == assigned_to)
    term = (search or "").strip()
    if term:
        pattern = contains_pattern(term)
        filters.append(
            or_(
                Contact.first_name.ilike(pattern, escape="\\"),
                Contact.last_name.ilike(pattern, escape="\\"),
                Contact.email.ilike(pattern, escape="\\"),
                Contact.phone.ilike(pattern, escape="\\"),
                Contact.company_name.ilike(pattern, escape="\\"),
            )
        )
    return filters


def _require_active_member(db: Session, company_id: UUID, user_id: UUID | None) -> None:
    if user_id is None:
        return
    membership_id = db.scalar(
        select(UserCompany.id).where(
            UserCompany.company_id == company_id,
            UserCompany.user_id == user_id,
            UserCompany.status == MembershipStatus.ACTIVE.value,
        )
    )
    if membership_id is None:
        raise BadRequestError("That person is not a member of this company.")


def _commit_contact(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if _is_email_conflict(exc):
            raise ConflictError(
                "A contact with this email already exists in this company."
            ) from None
        raise ConflictError("The contact could not be saved.") from None


def _is_email_conflict(exc: IntegrityError) -> bool:
    orig = getattr(exc, "orig", None)
    text = "" if orig is None else str(orig)
    return "uq_contacts_company_email" in text or "contacts.email" in text


def _list_item(contact: Contact, first_name: str | None, last_name: str | None) -> ContactListItem:
    return ContactListItem(
        id=contact.id,
        first_name=contact.first_name,
        last_name=contact.last_name,
        email=contact.email,
        phone=contact.phone,
        company_name=contact.company_name,
        status=ContactStatus(contact.status),
        source=ContactSource(contact.source),
        opted_in=contact.opted_in,
        contact_date=contact.contact_date,
        assigned_to_user_id=contact.assigned_to_user_id,
        assignee_name=_person_name(first_name, last_name),
        created_at=contact.created_at,
    )


def _detail(contact: Contact, first_name: str | None, last_name: str | None) -> ContactRead:
    listed = _list_item(contact, first_name, last_name)
    return ContactRead(
        **listed.model_dump(),
        address=contact.address,
        city=contact.city,
        state=contact.state,
        zip_code=contact.zip_code,
        notes=contact.notes,
        updated_at=contact.updated_at,
    )


def _person_name(first_name: str | None, last_name: str | None) -> str | None:
    if first_name is None or last_name is None:
        return None
    return f"{first_name} {last_name}"

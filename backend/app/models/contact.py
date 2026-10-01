"""Company-owned contact. Records are never global."""

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.permissions import ContactSource, ContactStatus, sql_in_list
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.user import User


class Contact(TimestampMixin, Base):
    __tablename__ = "contacts"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({sql_in_list(tuple(ContactStatus))})",
            name="status",
        ),
        CheckConstraint(
            f"source IN ({sql_in_list(tuple(ContactSource))})",
            name="source",
        ),
        CheckConstraint("length(trim(first_name)) > 0", name="first_name_not_blank"),
        CheckConstraint("length(trim(last_name)) > 0", name="last_name_not_blank"),
        UniqueConstraint("company_id", "email", name="uq_contacts_company_email"),
        Index("ix_contacts_company_created", "company_id", "created_at"),
        Index("ix_contacts_company_status", "company_id", "status"),
        Index("ix_contacts_company_assignee", "company_id", "assigned_to_user_id"),
        Index("ix_contacts_company_source", "company_id", "source"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=False,
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    company_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    zip_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ContactSource.MANUAL.value,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ContactStatus.ACTIVE.value,
    )
    opted_in: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    contact_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    assigned_to_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    company: Mapped["Company"] = relationship(lazy="raise")
    assignee: Mapped["User | None"] = relationship(lazy="raise")

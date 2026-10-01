"""Company-owned message. Delivery state is recorded only when a provider confirms it."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.permissions import MessageDirection, MessageStatus, MessageType, sql_in_list
from app.db.base import Base, TimestampMixin, UtcDateTime

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.contact import Contact
    from app.models.user import User


class Message(TimestampMixin, Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint(
            f"message_type IN ({sql_in_list(tuple(MessageType))})",
            name="message_type",
        ),
        CheckConstraint(
            f"direction IN ({sql_in_list(tuple(MessageDirection))})",
            name="direction",
        ),
        CheckConstraint(
            f"status IN ({sql_in_list(tuple(MessageStatus))})",
            name="status",
        ),
        CheckConstraint("length(trim(body)) > 0", name="body_not_blank"),
        Index("ix_messages_company_created", "company_id", "created_at"),
        Index("ix_messages_company_contact", "company_id", "contact_id"),
        Index("ix_messages_company_status", "company_id", "status"),
        Index("ix_messages_company_type", "company_id", "message_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=False,
    )
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("contacts.id", ondelete="RESTRICT"),
        nullable=True,
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    message_type: Mapped[str] = mapped_column(String(20), nullable=False)
    direction: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=MessageDirection.OUTBOUND.value,
    )
    subject: Mapped[str | None] = mapped_column(String(200), nullable=True)
    body: Mapped[str] = mapped_column(Text(), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=MessageStatus.DRAFT.value,
    )
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)

    company: Mapped["Company"] = relationship(lazy="raise")
    contact: Mapped["Contact | None"] = relationship(lazy="raise")
    created_by: Mapped["User | None"] = relationship(lazy="raise")

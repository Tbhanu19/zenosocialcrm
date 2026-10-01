"""User account. Platform super admins are flagged here and do not need a membership."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Index, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.permissions import UserStatus, sql_in_list
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user_company import UserCompany


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({sql_in_list(tuple(UserStatus))})",
            name="status",
        ),
        CheckConstraint("length(trim(email)) > 0", name="email_not_blank"),
        CheckConstraint("length(trim(first_name)) > 0", name="first_name_not_blank"),
        CheckConstraint("length(trim(last_name)) > 0", name="last_name_not_blank"),
        UniqueConstraint("email", name="uq_users_email"),
        Index("ix_users_status", "status"),
        Index("ix_users_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Unique constraint supports login lookup and rejects duplicate emails.
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # Supports filtering accounts by active, inactive, or invited status.
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=UserStatus.ACTIVE.value,
    )
    is_super_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Incremented on logout so previously issued access tokens stop working.
    token_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    # lazy="raise" forces callers to load memberships explicitly.
    memberships: Mapped[list["UserCompany"]] = relationship(
        back_populates="user",
        lazy="raise",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"User(id={self.id!s}, email={self.email!r})"

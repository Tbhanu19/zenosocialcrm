"""Membership linking a user to one company with exactly one role."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.permissions import (
    COMPANY_MEMBERSHIP_ROLES,
    MembershipStatus,
    sql_in_list,
)
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.user import User


class UserCompany(TimestampMixin, Base):
    __tablename__ = "user_companies"
    __table_args__ = (
        # One membership per user and company. The leftmost column also serves
        # "companies for this user" lookups, so a separate user_id index is not added.
        UniqueConstraint("user_id", "company_id", name="uq_user_companies_user_company"),
        # "members of this company" is not covered by the (user_id, company_id) index.
        Index("ix_user_companies_company_id", "company_id"),
        # Supports filtering memberships by role, such as all owners of a company set.
        Index("ix_user_companies_role", "role"),
        Index("ix_user_companies_status", "status"),
        # Role filters inside one company, such as the owners shown on the company list.
        Index("ix_user_companies_company_id_role", "company_id", "role"),
        CheckConstraint(
            f"role IN ({sql_in_list(COMPANY_MEMBERSHIP_ROLES)})",
            name="role",
        ),
        CheckConstraint(
            f"status IN ({sql_in_list(tuple(MembershipStatus))})",
            name="status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", name="fk_user_companies_user_id_users", ondelete="CASCADE"),
        nullable=False,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "companies.id",
            name="fk_user_companies_company_id_companies",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=MembershipStatus.ACTIVE.value,
    )

    user: Mapped["User"] = relationship(back_populates="memberships", lazy="raise")
    company: Mapped["Company"] = relationship(back_populates="memberships", lazy="raise")

    def __repr__(self) -> str:
        return (
            f"UserCompany(id={self.id!s}, user_id={self.user_id!s}, "
            f"company_id={self.company_id!s}, role={self.role!r})"
        )

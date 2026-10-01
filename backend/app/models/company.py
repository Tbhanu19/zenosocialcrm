"""Company tenant. CRM records in later phases must reference company_id."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.permissions import CompanyStatus, sql_in_list
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user_company import UserCompany


class Company(TimestampMixin, Base):
    __tablename__ = "companies"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({sql_in_list(tuple(CompanyStatus))})",
            name="status",
        ),
        CheckConstraint("length(trim(name)) > 0", name="name_not_blank"),
        Index("ix_companies_name", "name"),
        Index("ix_companies_status", "status"),
        Index("ix_companies_business_type", "business_type"),
        Index("ix_companies_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Supports ordering and lookup of companies by name.
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    business_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    zip_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Supports listing only active companies for non-admin access.
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=CompanyStatus.ACTIVE.value,
    )

    memberships: Mapped[list["UserCompany"]] = relationship(
        back_populates="company",
        lazy="raise",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"Company(id={self.id!s}, name={self.name!r})"

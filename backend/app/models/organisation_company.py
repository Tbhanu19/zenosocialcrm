"""Companies that belong to an organisation (tenant company record)."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.permissions import CompanyStatus, sql_in_list
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.company import Company


class OrganisationCompany(TimestampMixin, Base):
    __tablename__ = "organisation_companies"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({sql_in_list(tuple(CompanyStatus))})",
            name="status",
        ),
        CheckConstraint("length(trim(name)) > 0", name="name_not_blank"),
        Index("ix_org_companies_organisation", "organisation_id"),
        Index("ix_org_companies_organisation_name", "organisation_id", "name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    business_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=CompanyStatus.ACTIVE.value,
    )

    organisation: Mapped["Company"] = relationship(lazy="raise")

    def __repr__(self) -> str:
        return f"OrganisationCompany(id={self.id!s}, name={self.name!r})"

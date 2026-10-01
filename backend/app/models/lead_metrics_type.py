"""Company-owned lead metrics type labels."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.permissions import CompanyStatus, sql_in_list
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.company import Company


class LeadMetricsType(TimestampMixin, Base):
    __tablename__ = "lead_metrics_types"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({sql_in_list(tuple(CompanyStatus))})",
            name="status",
        ),
        CheckConstraint("length(trim(name)) > 0", name="name_not_blank"),
        Index("ix_lead_metrics_types_company_status", "company_id", "status"),
        Index("ix_lead_metrics_types_company_name", "company_id", "name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=CompanyStatus.ACTIVE.value,
    )

    company: Mapped["Company"] = relationship(lazy="raise")

    def __repr__(self) -> str:
        return f"LeadMetricsType(id={self.id!s}, name={self.name!r})"

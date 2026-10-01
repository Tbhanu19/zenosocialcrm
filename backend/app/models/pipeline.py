"""Company-owned sales pipeline. Stages belong to one pipeline."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.permissions import PipelineStatus, sql_in_list
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.company import Company


class SalesPipeline(TimestampMixin, Base):
    __tablename__ = "sales_pipelines"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({sql_in_list(tuple(PipelineStatus))})",
            name="status",
        ),
        CheckConstraint("length(trim(name)) > 0", name="name_not_blank"),
        Index("ix_pipelines_company_status", "company_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=PipelineStatus.ACTIVE.value,
    )

    company: Mapped["Company"] = relationship(lazy="raise")

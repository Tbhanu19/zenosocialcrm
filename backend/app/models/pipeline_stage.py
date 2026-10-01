"""Ordered stage inside one sales pipeline."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.permissions import StageColor, StageStatus, sql_in_list
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.pipeline import SalesPipeline


class SalesPipelineStage(TimestampMixin, Base):
    __tablename__ = "sales_pipeline_stages"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({sql_in_list(tuple(StageStatus))})",
            name="status",
        ),
        CheckConstraint(
            f"color IN ({sql_in_list(tuple(StageColor))})",
            name="color",
        ),
        CheckConstraint("length(trim(name)) > 0", name="name_not_blank"),
        CheckConstraint("position >= 1", name="position_positive"),
        UniqueConstraint("pipeline_id", "position", name="uq_pipeline_stages_position"),
        UniqueConstraint("pipeline_id", "id", name="uq_pipeline_stages_pipeline_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("sales_pipelines.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    position: Mapped[int] = mapped_column(Integer(), nullable=False)
    color: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=StageColor.COPPER.value,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=StageStatus.ACTIVE.value,
    )

    pipeline: Mapped["SalesPipeline"] = relationship(lazy="raise")

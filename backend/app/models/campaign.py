"""Company-owned marketing campaign. Records are never global."""

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.permissions import CampaignChannel, CampaignStatus, CampaignType, sql_in_list
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.user import User


class MarketingCampaign(TimestampMixin, Base):
    __tablename__ = "marketing_campaigns"
    __table_args__ = (
        CheckConstraint(
            f"campaign_type IN ({sql_in_list(tuple(CampaignType))})",
            name="type",
        ),
        CheckConstraint(
            f"channel IN ({sql_in_list(tuple(CampaignChannel))})",
            name="channel",
        ),
        CheckConstraint(
            f"status IN ({sql_in_list(tuple(CampaignStatus))})",
            name="status",
        ),
        CheckConstraint("length(trim(name)) > 0", name="name_not_blank"),
        CheckConstraint("budget IS NULL OR budget >= 0", name="budget_non_negative"),
        Index("ix_campaigns_company_created", "company_id", "created_at"),
        Index("ix_campaigns_company_status", "company_id", "status"),
        Index("ix_campaigns_company_start", "company_id", "start_date"),
        Index("ix_campaigns_company_end", "company_id", "end_date"),
        Index("ix_campaigns_company_channel", "company_id", "channel"),
        Index("ix_campaigns_company_type", "company_id", "campaign_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    campaign_type: Mapped[str] = mapped_column(String(20), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=CampaignStatus.DRAFT.value,
    )
    start_date: Mapped[date | None] = mapped_column(Date(), nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date(), nullable=True)
    budget: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    external_campaign_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    company: Mapped["Company"] = relationship(lazy="raise")
    created_by: Mapped["User | None"] = relationship(lazy="raise")

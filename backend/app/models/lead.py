"""Company-owned lead. Contact identity stays on the contact record."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.permissions import (
    LeadBusinessType,
    LeadPriority,
    LeadSource,
    LeadStatus,
    PreferredContactType,
    sql_in_list,
)
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.campaign import MarketingCampaign
    from app.models.company import Company
    from app.models.contact import Contact
    from app.models.pipeline import SalesPipeline
    from app.models.pipeline_stage import SalesPipelineStage
    from app.models.user import User


class Lead(TimestampMixin, Base):
    __tablename__ = "leads"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({sql_in_list(tuple(LeadStatus))})",
            name="status",
        ),
        CheckConstraint(
            f"source IN ({sql_in_list(tuple(LeadSource))})",
            name="source",
        ),
        CheckConstraint(
            f"priority IN ({sql_in_list(tuple(LeadPriority))})",
            name="priority",
        ),
        CheckConstraint("length(trim(title)) > 0", name="title_not_blank"),
        CheckConstraint(
            "company_name IS NULL OR length(trim(company_name)) > 0",
            name="company_name_not_blank",
        ),
        CheckConstraint(
            f"business_type IS NULL OR business_type IN ({sql_in_list(tuple(LeadBusinessType))})",
            name="business_type",
        ),
        CheckConstraint(
            "preferred_contact_type IS NULL OR preferred_contact_type IN "
            f"({sql_in_list(tuple(PreferredContactType))})",
            name="preferred_contact_type",
        ),
        CheckConstraint(
            "estimated_value IS NULL OR estimated_value >= 0",
            name="value_non_negative",
        ),
        Index("ix_leads_company_created", "company_id", "created_at"),
        Index("ix_leads_company_status", "company_id", "status"),
        Index("ix_leads_company_source", "company_id", "source"),
        Index("ix_leads_company_priority", "company_id", "priority"),
        Index("ix_leads_company_campaign", "company_id", "campaign_id"),
        Index("ix_leads_company_assignee", "company_id", "assigned_to_user_id"),
        Index("ix_leads_company_contact", "company_id", "contact_id"),
        Index("ix_leads_company_pipeline", "company_id", "pipeline_id"),
        Index("ix_leads_company_stage", "company_id", "pipeline_stage_id"),
        Index("ix_leads_company_close", "company_id", "expected_close_date"),
        Index("ix_leads_company_business_type", "company_id", "business_type"),
        CheckConstraint(
            "(pipeline_id IS NULL AND pipeline_stage_id IS NULL) "
            "OR (pipeline_id IS NOT NULL AND pipeline_stage_id IS NOT NULL)",
            name="pipeline_pair",
        ),
        ForeignKeyConstraint(
            ["pipeline_id", "pipeline_stage_id"],
            ["sales_pipeline_stages.pipeline_id", "sales_pipeline_stages.id"],
            name="fk_leads_pipeline_stage_pair",
        ),
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
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("marketing_campaigns.id", ondelete="RESTRICT"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    business_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(30), nullable=True)
    main_contact_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone_number_2: Mapped[str | None] = mapped_column(String(30), nullable=True)
    comments: Mapped[str | None] = mapped_column(Text(), nullable=True)
    preferred_contact_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    pipeline_created_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=LeadStatus.NEW.value,
    )
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=LeadPriority.MEDIUM.value,
    )
    assigned_to_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    estimated_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    expected_close_date: Mapped[date | None] = mapped_column(Date(), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    pipeline_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("sales_pipelines.id", ondelete="RESTRICT"),
        nullable=True,
    )
    pipeline_stage_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("sales_pipeline_stages.id", ondelete="RESTRICT"),
        nullable=True,
    )

    company: Mapped["Company"] = relationship(lazy="raise")
    contact: Mapped["Contact | None"] = relationship(lazy="raise")
    campaign: Mapped["MarketingCampaign | None"] = relationship(lazy="raise")
    assignee: Mapped["User | None"] = relationship(lazy="raise")
    pipeline: Mapped["SalesPipeline | None"] = relationship(
        lazy="raise",
        foreign_keys=[pipeline_id],
    )
    pipeline_stage: Mapped["SalesPipelineStage | None"] = relationship(
        lazy="raise",
        foreign_keys=[pipeline_stage_id],
    )

"""Marketing campaigns and leads.

Revision ID: 0005_marketing_leads
Revises: 0004_contacts_messages
Create Date: 2026-09-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

_MYSQL_TABLE = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_unicode_ci",
}

revision: str = "0005_marketing_leads"
down_revision: str | None = "0004_contacts_messages"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "marketing_campaigns",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("company_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("campaign_type", sa.String(length=20), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="draft", nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("budget", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("external_campaign_id", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_marketing_campaigns"),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name="fk_marketing_campaigns_company_id_companies",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_marketing_campaigns_created_by_user_id_users",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "campaign_type IN ('email', 'event', 'other', 'paid_ad', 'promotion', "
            "'referral', 'search', 'sms', 'social')",
            name="type",
        ),
        sa.CheckConstraint(
            "channel IN ('direct', 'email', 'facebook', 'google', 'instagram', "
            "'other', 'referral', 'sms', 'website')",
            name="channel",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'archived', 'completed', 'draft', 'paused')",
            name="status",
        ),
        sa.CheckConstraint("length(trim(name)) > 0", name="name_not_blank"),
        sa.CheckConstraint("budget IS NULL OR budget >= 0", name="budget_non_negative"),
        **_MYSQL_TABLE,
    )
    op.create_index(
        "ix_campaigns_company_created",
        "marketing_campaigns",
        ["company_id", "created_at"],
    )
    op.create_index(
        "ix_campaigns_company_status",
        "marketing_campaigns",
        ["company_id", "status"],
    )
    op.create_index(
        "ix_campaigns_company_start",
        "marketing_campaigns",
        ["company_id", "start_date"],
    )
    op.create_index(
        "ix_campaigns_company_end",
        "marketing_campaigns",
        ["company_id", "end_date"],
    )
    op.create_index(
        "ix_campaigns_company_channel",
        "marketing_campaigns",
        ["company_id", "channel"],
    )
    op.create_index(
        "ix_campaigns_company_type",
        "marketing_campaigns",
        ["company_id", "campaign_type"],
    )

    op.create_table(
        "leads",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("company_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("contact_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("campaign_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="new", nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("priority", sa.String(length=20), server_default="medium", nullable=False),
        sa.Column("assigned_to_user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("estimated_value", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("expected_close_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_leads"),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name="fk_leads_company_id_companies",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["contact_id"],
            ["contacts.id"],
            name="fk_leads_contact_id_contacts",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["marketing_campaigns.id"],
            name="fk_leads_campaign_id_marketing_campaigns",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_to_user_id"],
            ["users.id"],
            name="fk_leads_assigned_to_user_id_users",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "status IN ('archived', 'contacted', 'converted', 'lost', 'new', "
            "'qualified', 'unqualified')",
            name="status",
        ),
        sa.CheckConstraint(
            "source IN ('campaign', 'email', 'facebook', 'google', 'instagram', "
            "'manual', 'other', 'referral', 'sms', 'website')",
            name="source",
        ),
        sa.CheckConstraint("priority IN ('high', 'low', 'medium')", name="priority"),
        sa.CheckConstraint("length(trim(title)) > 0", name="title_not_blank"),
        sa.CheckConstraint(
            "estimated_value IS NULL OR estimated_value >= 0",
            name="value_non_negative",
        ),
        **_MYSQL_TABLE,
    )
    op.create_index("ix_leads_company_created", "leads", ["company_id", "created_at"])
    op.create_index("ix_leads_company_status", "leads", ["company_id", "status"])
    op.create_index("ix_leads_company_source", "leads", ["company_id", "source"])
    op.create_index("ix_leads_company_priority", "leads", ["company_id", "priority"])
    op.create_index("ix_leads_company_campaign", "leads", ["company_id", "campaign_id"])
    op.create_index("ix_leads_company_assignee", "leads", ["company_id", "assigned_to_user_id"])
    op.create_index("ix_leads_company_contact", "leads", ["company_id", "contact_id"])


def downgrade() -> None:
    # Drop the tables directly. MySQL uses the company indexes to support the
    # foreign keys, so removing those indexes first is rejected.
    op.drop_table("leads")
    op.drop_table("marketing_campaigns")

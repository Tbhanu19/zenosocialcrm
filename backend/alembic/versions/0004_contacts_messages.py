"""Contacts and messages.

Revision ID: 0004_contacts_messages
Revises: 0003_company_users
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

revision: str = "0004_contacts_messages"
down_revision: str | None = "0003_company_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "contacts",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("company_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("company_name", sa.String(length=200), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("zip_code", sa.String(length=20), nullable=True),
        sa.Column("source", sa.String(length=20), server_default="manual", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("assigned_to_user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_contacts"),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name="fk_contacts_company_id_companies",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_to_user_id"],
            ["users.id"],
            name="fk_contacts_assigned_to_user_id_users",
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("company_id", "email", name="uq_contacts_company_email"),
        sa.CheckConstraint(
            "status IN ('active', 'archived', 'inactive')",
            name="status",
        ),
        sa.CheckConstraint(
            "source IN ('campaign', 'import', 'manual', 'other', 'referral', 'website')",
            name="source",
        ),
        sa.CheckConstraint("length(trim(first_name)) > 0", name="first_name_not_blank"),
        sa.CheckConstraint("length(trim(last_name)) > 0", name="last_name_not_blank"),
        **_MYSQL_TABLE,
    )
    op.create_index("ix_contacts_company_created", "contacts", ["company_id", "created_at"])
    op.create_index("ix_contacts_company_status", "contacts", ["company_id", "status"])
    op.create_index(
        "ix_contacts_company_assignee",
        "contacts",
        ["company_id", "assigned_to_user_id"],
    )
    op.create_index("ix_contacts_company_source", "contacts", ["company_id", "source"])

    op.create_table(
        "messages",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("company_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("contact_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("message_type", sa.String(length=20), nullable=False),
        sa.Column("direction", sa.String(length=20), server_default="outbound", nullable=False),
        sa.Column("subject", sa.String(length=200), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="draft", nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=True),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_messages"),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name="fk_messages_company_id_companies",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["contact_id"],
            ["contacts.id"],
            name="fk_messages_contact_id_contacts",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_messages_created_by_user_id_users",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint("message_type IN ('email', 'sms')", name="message_type"),
        sa.CheckConstraint("direction IN ('inbound', 'outbound')", name="direction"),
        sa.CheckConstraint(
            "status IN ('delivered', 'draft', 'failed', 'queued', 'sent')",
            name="status",
        ),
        sa.CheckConstraint("length(trim(body)) > 0", name="body_not_blank"),
        **_MYSQL_TABLE,
    )
    op.create_index("ix_messages_company_created", "messages", ["company_id", "created_at"])
    op.create_index("ix_messages_company_contact", "messages", ["company_id", "contact_id"])
    op.create_index("ix_messages_company_status", "messages", ["company_id", "status"])
    op.create_index("ix_messages_company_type", "messages", ["company_id", "message_type"])


def downgrade() -> None:
    # Drop the tables directly. MySQL uses the company indexes to support the
    # foreign keys, so removing those indexes first is rejected.
    op.drop_table("messages")
    op.drop_table("contacts")

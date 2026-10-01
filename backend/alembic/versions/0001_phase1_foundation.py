"""Phase 1 multi-tenant foundation: users, companies, and memberships.

Revision ID: 0001_phase1
Revises:
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

revision: str = "0001_phase1"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column(
            "is_super_admin",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.CheckConstraint(
            "status IN ('active', 'inactive', 'invited')",
            name="status",
        ),
        sa.CheckConstraint("length(trim(email)) > 0", name="email_not_blank"),
        sa.CheckConstraint("length(trim(first_name)) > 0", name="first_name_not_blank"),
        sa.CheckConstraint("length(trim(last_name)) > 0", name="last_name_not_blank"),
        **_MYSQL_TABLE,
    )
    # Login looks up a user by email through uq_users_email.
    # Status filters support active, inactive, and invited account lists.
    op.create_index("ix_users_status", "users", ["status"])

    op.create_table(
        "companies",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("business_type", sa.String(length=100), nullable=True),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("website", sa.String(length=500), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("zip_code", sa.String(length=20), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_companies"),
        sa.CheckConstraint(
            "status IN ('active', 'inactive')",
            name="status",
        ),
        sa.CheckConstraint("length(trim(name)) > 0", name="name_not_blank"),
        **_MYSQL_TABLE,
    )
    # Name supports ordered company lists. Status supports active-company filters.
    op.create_index("ix_companies_name", "companies", ["name"])
    op.create_index("ix_companies_status", "companies", ["status"])

    op.create_table(
        "user_companies",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("company_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_user_companies"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_companies_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name="fk_user_companies_company_id_companies",
            ondelete="CASCADE",
        ),
        # One role per user per company. Also serves lookups by user_id.
        sa.UniqueConstraint("user_id", "company_id", name="uq_user_companies_user_company"),
        sa.CheckConstraint(
            "role IN ('company_manager', 'employee', 'marketing_manager', 'owner')",
            name="role",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'inactive')",
            name="status",
        ),
        # Created with the table so MySQL can use it for the company foreign key.
        sa.Index("ix_user_companies_company_id", "company_id"),
        **_MYSQL_TABLE,
    )
    # Role filters support questions such as "which owners belong to these companies".
    op.create_index("ix_user_companies_role", "user_companies", ["role"])


def downgrade() -> None:
    op.drop_table("user_companies")
    op.drop_table("companies")
    op.drop_table("users")

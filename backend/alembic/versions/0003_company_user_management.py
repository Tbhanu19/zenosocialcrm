"""Indexes and user phone for company and user management.

Revision ID: 0003_company_users
Revises: 0002_token_version
Create Date: 2026-09-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_company_users"
down_revision: str | None = "0002_token_version"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("phone", sa.String(length=30), nullable=True))
    op.create_index("ix_users_created_at", "users", ["created_at"])
    op.create_index("ix_companies_business_type", "companies", ["business_type"])
    op.create_index("ix_companies_created_at", "companies", ["created_at"])
    op.create_index("ix_user_companies_status", "user_companies", ["status"])
    op.create_index(
        "ix_user_companies_company_id_role",
        "user_companies",
        ["company_id", "role"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_companies_company_id_role", table_name="user_companies")
    op.drop_index("ix_user_companies_status", table_name="user_companies")
    op.drop_index("ix_companies_created_at", table_name="companies")
    op.drop_index("ix_companies_business_type", table_name="companies")
    op.drop_index("ix_users_created_at", table_name="users")
    op.drop_column("users", "phone")

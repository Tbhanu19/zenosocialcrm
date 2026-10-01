"""Add business_type to organisation companies.

Revision ID: 0011_org_company_business_type
Revises: 0010_organisation_companies
Create Date: 2026-10-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_org_company_business_type"
down_revision: str | None = "0010_organisation_companies"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "organisation_companies",
        sa.Column("business_type", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("organisation_companies", "business_type")

"""Add companies nested under organisations.

Revision ID: 0010_organisation_companies
Revises: 0009_lead_pipeline_entry
Create Date: 2026-10-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_organisation_companies"
down_revision: str | None = "0009_lead_pipeline_entry"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organisation_companies",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("organisation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("status IN ('active', 'inactive')", name="ck_organisation_companies_status"),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_organisation_companies_name_not_blank"),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["companies.id"],
            name="fk_organisation_companies_organisation_id_companies",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_organisation_companies"),
    )
    op.create_index(
        "ix_org_companies_organisation",
        "organisation_companies",
        ["organisation_id"],
    )
    op.create_index(
        "ix_org_companies_organisation_name",
        "organisation_companies",
        ["organisation_id", "name"],
    )


def downgrade() -> None:
    op.drop_index("ix_org_companies_organisation_name", table_name="organisation_companies")
    op.drop_index("ix_org_companies_organisation", table_name="organisation_companies")
    op.drop_table("organisation_companies")

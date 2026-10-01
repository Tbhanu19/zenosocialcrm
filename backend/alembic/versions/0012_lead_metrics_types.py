"""Add lead metrics types table.

Revision ID: 0012_lead_metrics_types
Revises: 0011_org_company_business_type
Create Date: 2026-10-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_lead_metrics_types"
down_revision: str | None = "0011_org_company_business_type"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lead_metrics_types",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("company_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('active', 'inactive')",
            name="ck_lead_metrics_types_status",
        ),
        sa.CheckConstraint(
            "length(trim(name)) > 0",
            name="ck_lead_metrics_types_name_not_blank",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name="fk_lead_metrics_types_company_id_companies",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_lead_metrics_types"),
    )
    op.create_index(
        "ix_lead_metrics_types_company_status",
        "lead_metrics_types",
        ["company_id", "status"],
    )
    op.create_index(
        "ix_lead_metrics_types_company_name",
        "lead_metrics_types",
        ["company_id", "name"],
    )


def downgrade() -> None:
    op.drop_index("ix_lead_metrics_types_company_name", table_name="lead_metrics_types")
    op.drop_index("ix_lead_metrics_types_company_status", table_name="lead_metrics_types")
    op.drop_table("lead_metrics_types")

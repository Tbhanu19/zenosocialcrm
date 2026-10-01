"""Prospect fields for hotel, plumbing, and HVAC leads.

Revision ID: 0007_lead_prospect_fields
Revises: 0006_metrics_pipeline
Create Date: 2026-10-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_lead_prospect_fields"
down_revision: str | None = "0006_metrics_pipeline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("leads", sa.Column("company_name", sa.String(length=200), nullable=True))
    op.add_column("leads", sa.Column("business_type", sa.String(length=20), nullable=True))
    op.add_column("leads", sa.Column("address", sa.String(length=255), nullable=True))
    op.add_column("leads", sa.Column("phone_number", sa.String(length=30), nullable=True))
    op.add_column("leads", sa.Column("current_provider", sa.String(length=200), nullable=True))
    op.add_column("leads", sa.Column("main_contact_name", sa.String(length=200), nullable=True))
    op.add_column("leads", sa.Column("email", sa.String(length=320), nullable=True))
    op.add_column("leads", sa.Column("phone_number_2", sa.String(length=30), nullable=True))
    op.add_column("leads", sa.Column("hotel_brand_type", sa.String(length=200), nullable=True))
    op.add_column("leads", sa.Column("comments", sa.Text(), nullable=True))
    op.create_index("ix_leads_company_business_type", "leads", ["company_id", "business_type"])


def downgrade() -> None:
    op.drop_index("ix_leads_company_business_type", table_name="leads")
    op.drop_column("leads", "comments")
    op.drop_column("leads", "hotel_brand_type")
    op.drop_column("leads", "phone_number_2")
    op.drop_column("leads", "email")
    op.drop_column("leads", "main_contact_name")
    op.drop_column("leads", "current_provider")
    op.drop_column("leads", "phone_number")
    op.drop_column("leads", "address")
    op.drop_column("leads", "business_type")
    op.drop_column("leads", "company_name")

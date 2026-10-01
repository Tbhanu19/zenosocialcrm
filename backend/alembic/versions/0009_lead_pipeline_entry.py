"""Preferred contact type and pipeline created time on leads.

Revision ID: 0009_lead_pipeline_entry
Revises: 0008_drop_lead_provider_brand
Create Date: 2026-10-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_lead_pipeline_entry"
down_revision: str | None = "0008_drop_lead_provider_brand"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("leads", sa.Column("preferred_contact_type", sa.String(length=20), nullable=True))
    op.add_column("leads", sa.Column("pipeline_created_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("leads", "pipeline_created_at")
    op.drop_column("leads", "preferred_contact_type")

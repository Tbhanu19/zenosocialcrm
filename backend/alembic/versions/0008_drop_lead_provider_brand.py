"""Drop unused lead prospect columns.

Revision ID: 0008_drop_lead_provider_brand
Revises: 0007_lead_prospect_fields
Create Date: 2026-10-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_drop_lead_provider_brand"
down_revision: str | None = "0007_lead_prospect_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("leads", "hotel_brand_type")
    op.drop_column("leads", "current_provider")


def downgrade() -> None:
    op.add_column("leads", sa.Column("current_provider", sa.String(length=200), nullable=True))
    op.add_column("leads", sa.Column("hotel_brand_type", sa.String(length=200), nullable=True))

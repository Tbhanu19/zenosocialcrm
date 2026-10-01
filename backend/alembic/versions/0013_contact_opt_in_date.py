"""Add opted_in and contact_date to contacts.

Revision ID: 0013_contact_opt_in_date
Revises: 0012_lead_metrics_types
Create Date: 2026-10-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_contact_opt_in_date"
down_revision: str | None = "0012_lead_metrics_types"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("contacts") as batch_op:
        batch_op.add_column(
            sa.Column("opted_in", sa.Boolean(), server_default=sa.true(), nullable=False)
        )
        batch_op.add_column(sa.Column("contact_date", sa.Date(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("contacts") as batch_op:
        batch_op.drop_column("contact_date")
        batch_op.drop_column("opted_in")

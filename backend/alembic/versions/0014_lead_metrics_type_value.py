"""Add value to lead metrics types.

Revision ID: 0014_lead_metrics_type_value
Revises: 0013_contact_opt_in_date
Create Date: 2026-10-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_lead_metrics_type_value"
down_revision: str | None = "0013_contact_opt_in_date"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("lead_metrics_types") as batch_op:
        batch_op.add_column(
            sa.Column("value", sa.Integer(), server_default="0", nullable=False)
        )


def downgrade() -> None:
    with op.batch_alter_table("lead_metrics_types") as batch_op:
        batch_op.drop_column("value")

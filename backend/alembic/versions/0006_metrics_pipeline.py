"""Sales pipelines, stages, and lead pipeline fields.

Revision ID: 0006_metrics_pipeline
Revises: 0005_marketing_leads
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

revision: str = "0006_metrics_pipeline"
down_revision: str | None = "0005_marketing_leads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sales_pipelines",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("company_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_sales_pipelines"),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name="fk_sales_pipelines_company_id_companies",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("status IN ('active', 'archived')", name="status"),
        sa.CheckConstraint("length(trim(name)) > 0", name="name_not_blank"),
        **_MYSQL_TABLE,
    )
    op.create_index(
        "ix_pipelines_company_status",
        "sales_pipelines",
        ["company_id", "status"],
    )

    op.create_table(
        "sales_pipeline_stages",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("pipeline_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("color", sa.String(length=20), server_default="copper", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_sales_pipeline_stages"),
        sa.ForeignKeyConstraint(
            ["pipeline_id"],
            ["sales_pipelines.id"],
            name="fk_sales_pipeline_stages_pipeline_id_sales_pipelines",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("pipeline_id", "position", name="uq_pipeline_stages_position"),
        sa.UniqueConstraint("pipeline_id", "id", name="uq_pipeline_stages_pipeline_id"),
        sa.CheckConstraint("status IN ('active', 'inactive')", name="status"),
        sa.CheckConstraint(
            "color IN ('copper', 'danger', 'ink', 'moss', 'pine')",
            name="color",
        ),
        sa.CheckConstraint("length(trim(name)) > 0", name="name_not_blank"),
        sa.CheckConstraint("position >= 1", name="position_positive"),
        **_MYSQL_TABLE,
    )

    pipeline_id = sa.Column("pipeline_id", sa.Uuid(as_uuid=True), nullable=True)
    pipeline_stage_id = sa.Column("pipeline_stage_id", sa.Uuid(as_uuid=True), nullable=True)
    pair_check = (
        "(pipeline_id IS NULL AND pipeline_stage_id IS NULL) "
        "OR (pipeline_id IS NOT NULL AND pipeline_stage_id IS NOT NULL)"
    )
    # SQLite cannot ALTER existing tables to add foreign keys or checks.
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("leads") as batch:
            batch.add_column(pipeline_id)
            batch.add_column(pipeline_stage_id)
            batch.create_foreign_key(
                "fk_leads_pipeline_id_sales_pipelines",
                "sales_pipelines",
                ["pipeline_id"],
                ["id"],
                ondelete="RESTRICT",
            )
            batch.create_foreign_key(
                "fk_leads_pipeline_stage_id_sales_pipeline_stages",
                "sales_pipeline_stages",
                ["pipeline_stage_id"],
                ["id"],
                ondelete="RESTRICT",
            )
            batch.create_foreign_key(
                "fk_leads_pipeline_stage_pair",
                "sales_pipeline_stages",
                ["pipeline_id", "pipeline_stage_id"],
                ["pipeline_id", "id"],
                ondelete="RESTRICT",
            )
            batch.create_check_constraint("ck_leads_pipeline_pair", pair_check)
    else:
        op.add_column("leads", pipeline_id)
        op.add_column("leads", pipeline_stage_id)
        op.create_foreign_key(
            "fk_leads_pipeline_id_sales_pipelines",
            "leads",
            "sales_pipelines",
            ["pipeline_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        op.create_foreign_key(
            "fk_leads_pipeline_stage_id_sales_pipeline_stages",
            "leads",
            "sales_pipeline_stages",
            ["pipeline_stage_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        op.create_foreign_key(
            "fk_leads_pipeline_stage_pair",
            "leads",
            "sales_pipeline_stages",
            ["pipeline_id", "pipeline_stage_id"],
            ["pipeline_id", "id"],
            ondelete="RESTRICT",
        )
        op.create_check_constraint("ck_leads_pipeline_pair", "leads", pair_check)
    op.create_index("ix_leads_company_pipeline", "leads", ["company_id", "pipeline_id"])
    op.create_index("ix_leads_company_stage", "leads", ["company_id", "pipeline_stage_id"])
    op.create_index("ix_leads_company_close", "leads", ["company_id", "expected_close_date"])


def downgrade() -> None:
    op.drop_index("ix_leads_company_close", table_name="leads")
    op.drop_index("ix_leads_company_stage", table_name="leads")
    op.drop_index("ix_leads_company_pipeline", table_name="leads")
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("leads") as batch:
            batch.drop_constraint("ck_leads_pipeline_pair", type_="check")
            batch.drop_constraint("fk_leads_pipeline_stage_pair", type_="foreignkey")
            batch.drop_constraint(
                "fk_leads_pipeline_stage_id_sales_pipeline_stages",
                type_="foreignkey",
            )
            batch.drop_constraint("fk_leads_pipeline_id_sales_pipelines", type_="foreignkey")
            batch.drop_column("pipeline_stage_id")
            batch.drop_column("pipeline_id")
    else:
        op.drop_constraint("ck_leads_pipeline_pair", "leads", type_="check")
        op.drop_constraint("fk_leads_pipeline_stage_pair", "leads", type_="foreignkey")
        op.drop_constraint(
            "fk_leads_pipeline_stage_id_sales_pipeline_stages",
            "leads",
            type_="foreignkey",
        )
        op.drop_constraint("fk_leads_pipeline_id_sales_pipelines", "leads", type_="foreignkey")
        op.drop_column("leads", "pipeline_stage_id")
        op.drop_column("leads", "pipeline_id")
    op.drop_table("sales_pipeline_stages")
    op.drop_table("sales_pipelines")

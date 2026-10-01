"""Sales metric aggregates. These schemas never include lead rows."""

from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.permissions import LeadSource


class SalesMetricSummary(BaseModel):
    total_opportunities: int
    total_pipeline_value: str
    converted_leads: int
    converted_value: str
    lost_leads: int
    lost_value: str
    conversion_rate: str
    average_opportunity_value: str


class SalesStageMetric(BaseModel):
    stage_id: UUID | None
    stage_name: str | None
    position: int | None
    lead_count: int
    pipeline_value: str
    converted_count: int
    converted_value: str


class SalesSourceMetric(BaseModel):
    source: LeadSource
    lead_count: int
    pipeline_value: str
    converted_count: int
    converted_value: str


class SalesCampaignMetric(BaseModel):
    campaign_id: UUID | None
    campaign_name: str | None
    lead_count: int
    pipeline_value: str
    converted_count: int
    converted_value: str


class SalesUserMetric(BaseModel):
    user_id: UUID | None
    user_name: str | None
    opportunity_count: int
    pipeline_value: str
    converted_count: int
    converted_value: str


class SalesTrendPoint(BaseModel):
    period: str
    opportunity_count: int
    pipeline_value: str
    converted_count: int
    converted_value: str


class ExpectedCloseMetrics(BaseModel):
    upcoming_count: int
    upcoming_value: str
    overdue_count: int
    overdue_value: str


class SalesCycleStatus(BaseModel):
    available: bool
    reason: str | None = None


class SalesMetrics(BaseModel):
    """interval is day, week, or month, chosen from the requested date span."""

    interval: str = Field(pattern="^(day|week|month)$")
    summary: SalesMetricSummary
    by_stage: list[SalesStageMetric]
    by_source: list[SalesSourceMetric]
    by_campaign: list[SalesCampaignMetric]
    by_assigned_user: list[SalesUserMetric]
    trend: list[SalesTrendPoint]
    expected_close: ExpectedCloseMetrics
    sales_cycle: SalesCycleStatus


def money_amount(value: object) -> str:
    if value is None:
        return "0.00"
    amount = value if isinstance(value, Decimal) else Decimal(str(value))
    quantized = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{quantized:.2f}"


def average_amount(total: object, count: int) -> str:
    if count <= 0:
        return "0.00"
    amount = total if isinstance(total, Decimal) else Decimal(str(total or 0))
    return money_amount(amount / Decimal(count))

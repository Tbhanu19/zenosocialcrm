"""Lead metric aggregates. These schemas never include lead rows."""

from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.permissions import LeadSource, LeadStatus


class LeadMetricSummary(BaseModel):
    total_leads: int
    new_leads: int
    contacted_leads: int
    qualified_leads: int
    unqualified_leads: int
    converted_leads: int
    lost_leads: int
    conversion_rate: str


class LeadStatusCount(BaseModel):
    status: LeadStatus
    count: int


class LeadSourceCount(BaseModel):
    source: LeadSource
    count: int


class LeadCampaignCount(BaseModel):
    campaign_id: UUID | None
    campaign_name: str | None
    lead_count: int
    converted_count: int


class LeadTimePoint(BaseModel):
    period: str
    lead_count: int
    converted_count: int


class LeadMetrics(BaseModel):
    """interval is day, week, or month, chosen from the requested date span."""

    interval: str = Field(pattern="^(day|week|month)$")
    summary: LeadMetricSummary
    by_status: list[LeadStatusCount]
    by_source: list[LeadSourceCount]
    by_campaign: list[LeadCampaignCount]
    over_time: list[LeadTimePoint]


def rate_text(converted: int, total: int) -> str:
    if total <= 0:
        return "0.00"
    value = (Decimal(converted) * Decimal(100) / Decimal(total)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )
    return f"{value:.2f}"

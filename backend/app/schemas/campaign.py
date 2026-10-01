"""Campaign request and response schemas. Company id is taken from the path."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.permissions import CampaignChannel, CampaignStatus, CampaignType


class CampaignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    campaign_type: CampaignType
    channel: CampaignChannel
    status: CampaignStatus = CampaignStatus.DRAFT
    start_date: date | None = None
    end_date: date | None = None
    budget: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    source: str | None = Field(default=None, max_length=100)
    external_campaign_id: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Name is required.")
        return cleaned

    @field_validator("description", "source", "external_campaign_id", "notes")
    @classmethod
    def empty_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode="after")
    def dates_in_order(self) -> "CampaignCreate":
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.end_date < self.start_date
        ):
            raise ValueError("End date must be on or after the start date.")
        return self


class CampaignUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    campaign_type: CampaignType | None = None
    channel: CampaignChannel | None = None
    status: CampaignStatus | None = None
    start_date: date | None = None
    end_date: date | None = None
    budget: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    source: str | None = Field(default=None, max_length=100)
    external_campaign_id: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Name is required.")
        return cleaned

    @field_validator("description", "source", "external_campaign_id", "notes")
    @classmethod
    def empty_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class CampaignListItem(BaseModel):
    id: UUID
    name: str
    campaign_type: CampaignType
    channel: CampaignChannel
    status: CampaignStatus
    start_date: date | None
    end_date: date | None
    budget: str | None
    source: str | None
    created_at: datetime


class CampaignRead(CampaignListItem):
    description: str | None
    external_campaign_id: str | None
    notes: str | None
    created_by_user_id: UUID | None
    creator_name: str | None
    updated_at: datetime


class MarketingSummary(BaseModel):
    active_campaigns: int
    total_leads: int
    new_leads: int
    converted_leads: int

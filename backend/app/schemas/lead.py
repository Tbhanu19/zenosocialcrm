"""Lead request and response schemas. Company id is taken from the path."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.core.permissions import (
    CampaignStatus,
    LeadBusinessType,
    LeadPriority,
    LeadSource,
    LeadStatus,
    PreferredContactType,
)
from app.core.phone import UsPhone


class LeadCreate(BaseModel):
    contact_id: UUID | None = None
    campaign_id: UUID | None = None
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: LeadStatus = LeadStatus.NEW
    source: LeadSource
    priority: LeadPriority = LeadPriority.MEDIUM
    assigned_to_user_id: UUID | None = None
    estimated_value: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    expected_close_date: date | None = None
    notes: str | None = Field(default=None, max_length=5000)
    company_name: str | None = Field(default=None, max_length=200)
    business_type: LeadBusinessType | None = None
    address: str | None = Field(default=None, max_length=255)
    phone_number: UsPhone = Field(default=None, max_length=30)
    main_contact_name: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=320)
    phone_number_2: UsPhone = Field(default=None, max_length=30)
    comments: str | None = Field(default=None, max_length=5000)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Title is required.")
        return cleaned

    @field_validator(
        "description",
        "notes",
        "company_name",
        "address",
        "phone_number",
        "main_contact_name",
        "email",
        "phone_number_2",
        "comments",
    )
    @classmethod
    def empty_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("email")
    @classmethod
    def email_shape(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if "@" not in value or "." not in value.split("@", 1)[1]:
            raise ValueError("Enter a valid email.")
        return value

    @field_validator("status")
    @classmethod
    def create_status_is_open(cls, value: LeadStatus) -> LeadStatus:
        if value is LeadStatus.ARCHIVED:
            raise ValueError("Create the lead before archiving it.")
        return value


class LeadUpdate(BaseModel):
    contact_id: UUID | None = None
    campaign_id: UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: LeadStatus | None = None
    source: LeadSource | None = None
    priority: LeadPriority | None = None
    assigned_to_user_id: UUID | None = None
    estimated_value: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    expected_close_date: date | None = None
    notes: str | None = Field(default=None, max_length=5000)
    company_name: str | None = Field(default=None, max_length=200)
    business_type: LeadBusinessType | None = None
    address: str | None = Field(default=None, max_length=255)
    phone_number: UsPhone = Field(default=None, max_length=30)
    main_contact_name: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=320)
    phone_number_2: UsPhone = Field(default=None, max_length=30)
    comments: str | None = Field(default=None, max_length=5000)
    preferred_contact_type: PreferredContactType | None = None
    pipeline_created_at: datetime | None = None

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Title is required.")
        return cleaned

    @field_validator(
        "description",
        "notes",
        "company_name",
        "address",
        "phone_number",
        "main_contact_name",
        "email",
        "phone_number_2",
        "comments",
    )
    @classmethod
    def empty_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("email")
    @classmethod
    def email_shape(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if "@" not in value or "." not in value.split("@", 1)[1]:
            raise ValueError("Enter a valid email.")
        return value


class LeadListItem(BaseModel):
    id: UUID
    title: str
    status: LeadStatus
    priority: LeadPriority
    source: LeadSource
    contact_id: UUID | None
    contact_name: str | None
    campaign_id: UUID | None
    campaign_name: str | None
    campaign_status: CampaignStatus | None
    assigned_to_user_id: UUID | None
    assignee_name: str | None
    estimated_value: str | None
    created_at: datetime
    company_name: str | None = None
    business_type: LeadBusinessType | None = None
    address: str | None = None
    phone_number: str | None = None
    main_contact_name: str | None = None
    email: str | None = None
    phone_number_2: str | None = None
    comments: str | None = None
    preferred_contact_type: PreferredContactType | None = None
    pipeline_created_at: datetime | None = None


class LeadRead(LeadListItem):
    description: str | None
    notes: str | None
    expected_close_date: date | None
    updated_at: datetime
    pipeline_id: UUID | None = None
    pipeline_stage_id: UUID | None = None
    pipeline_name: str | None = None
    stage_name: str | None = None

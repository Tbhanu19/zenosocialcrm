"""Lead metrics type request and response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.core.permissions import CompanyStatus


class LeadMetricsTypeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    value: int = Field(default=0, ge=0)
    status: CompanyStatus = CompanyStatus.ACTIVE

    @field_validator("name")
    @classmethod
    def name_must_contain_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Lead metrics type name is required.")
        return cleaned

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class LeadMetricsTypeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    value: int | None = Field(default=None, ge=0)
    status: CompanyStatus | None = None

    @field_validator("name")
    @classmethod
    def name_must_contain_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Lead metrics type name is required.")
        return cleaned

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class LeadMetricsTypeRead(BaseModel):
    id: UUID
    company_id: UUID
    name: str
    description: str | None
    value: int
    status: CompanyStatus
    created_at: datetime
    updated_at: datetime

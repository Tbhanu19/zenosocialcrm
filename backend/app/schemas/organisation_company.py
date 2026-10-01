"""Companies nested under an organisation."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.permissions import CompanyStatus
from app.core.phone import UsPhone


class OrganisationCompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    business_type: str = Field(min_length=1, max_length=100)
    phone: UsPhone = Field(default=None, max_length=30)
    email: EmailStr | None = None
    status: CompanyStatus = CompanyStatus.ACTIVE

    @field_validator("name")
    @classmethod
    def name_must_contain_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Company name is required.")
        return cleaned

    @field_validator("business_type")
    @classmethod
    def business_type_must_contain_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Business type is required.")
        return cleaned

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr | None) -> str | None:
        if value is None:
            return None
        return str(value).strip().lower()


class OrganisationCompanyRead(BaseModel):
    id: UUID
    organisation_id: UUID
    name: str
    business_type: str | None
    phone: str | None
    email: str | None
    status: CompanyStatus
    created_at: datetime
    updated_at: datetime

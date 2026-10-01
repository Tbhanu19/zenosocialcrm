"""Contact request and response schemas. Company id is never taken from the body."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.permissions import ContactSource, ContactStatus
from app.core.phone import UsPhone


class ContactCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr | None = None
    phone: UsPhone = Field(default=None, max_length=30)
    company_name: str | None = Field(default=None, max_length=200)
    address: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    zip_code: str | None = Field(default=None, max_length=20)
    source: ContactSource = ContactSource.MANUAL
    status: ContactStatus = ContactStatus.ACTIVE
    opted_in: bool = True
    contact_date: date | None = None
    notes: str | None = Field(default=None, max_length=5000)
    assigned_to_user_id: UUID | None = None

    @field_validator("first_name", "last_name")
    @classmethod
    def strip_required_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Name is required.")
        return cleaned

    @field_validator(
        "phone",
        "company_name",
        "address",
        "city",
        "state",
        "zip_code",
        "notes",
    )
    @classmethod
    def empty_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr | None) -> str | None:
        if value is None:
            return None
        return str(value).strip().lower()

    @field_validator("status")
    @classmethod
    def create_status_is_visible(cls, value: ContactStatus) -> ContactStatus:
        if value is ContactStatus.ARCHIVED:
            raise ValueError("Create the contact before archiving it.")
        return value


class ContactUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    phone: UsPhone = Field(default=None, max_length=30)
    company_name: str | None = Field(default=None, max_length=200)
    address: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    zip_code: str | None = Field(default=None, max_length=20)
    source: ContactSource | None = None
    status: ContactStatus | None = None
    opted_in: bool | None = None
    contact_date: date | None = None
    notes: str | None = Field(default=None, max_length=5000)
    assigned_to_user_id: UUID | None = None

    @field_validator("first_name", "last_name")
    @classmethod
    def strip_optional_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Name is required.")
        return cleaned

    @field_validator(
        "phone",
        "company_name",
        "address",
        "city",
        "state",
        "zip_code",
        "notes",
    )
    @classmethod
    def empty_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr | None) -> str | None:
        if value is None:
            return None
        return str(value).strip().lower()


class ContactListItem(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    email: str | None
    phone: str | None
    company_name: str | None
    status: ContactStatus
    source: ContactSource
    opted_in: bool
    contact_date: date | None
    assigned_to_user_id: UUID | None
    assignee_name: str | None
    created_at: datetime


class ContactRead(ContactListItem):
    address: str | None
    city: str | None
    state: str | None
    zip_code: str | None
    notes: str | None
    updated_at: datetime


class AssigneeOption(BaseModel):
    id: UUID
    first_name: str
    last_name: str

"""Company and membership schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.permissions import CompanyStatus, MembershipStatus, UserRole, UserStatus
from app.core.phone import UsPhone


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    business_type: str | None = Field(default=None, max_length=100)
    phone: UsPhone = Field(default=None, max_length=30)
    email: EmailStr | None = None
    website: str | None = Field(default=None, max_length=500)
    address: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    zip_code: str | None = Field(default=None, max_length=20)
    status: CompanyStatus = CompanyStatus.ACTIVE

    @field_validator("name")
    @classmethod
    def name_must_contain_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Company name is required.")
        return cleaned

    @field_validator(
        "business_type",
        "website",
        "address",
        "city",
        "state",
        "zip_code",
    )
    @classmethod
    def empty_string_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr | None) -> str | None:
        if value is None:
            return None
        return value.strip().lower()


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    business_type: str | None
    phone: str | None
    email: str | None
    website: str | None
    address: str | None
    city: str | None
    state: str | None
    zip_code: str | None
    status: CompanyStatus
    created_at: datetime
    updated_at: datetime


class AvailableCompanyRead(BaseModel):
    id: UUID
    name: str
    role: UserRole
    status: CompanyStatus


class CompanyAccessRead(CompanyRead):
    role: UserRole


class OwnerSeed(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    phone: UsPhone = Field(default=None, max_length=30)

    @field_validator("first_name", "last_name")
    @classmethod
    def strip_required_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Name is required.")
        return cleaned

    def normalized_email(self) -> str:
        return str(self.email).strip().lower()


class AdminCompanyCreate(CompanyCreate):
    business_type: str = Field(min_length=1, max_length=100)
    owner: OwnerSeed


class CompanyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    business_type: str | None = Field(default=None, max_length=100)
    phone: UsPhone = Field(default=None, max_length=30)
    email: EmailStr | None = None
    website: str | None = Field(default=None, max_length=500)
    address: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    zip_code: str | None = Field(default=None, max_length=20)
    status: CompanyStatus | None = None

    @field_validator("name")
    @classmethod
    def name_must_contain_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Company name is required.")
        return cleaned

    @field_validator(
        "business_type",
        "website",
        "address",
        "city",
        "state",
        "zip_code",
    )
    @classmethod
    def empty_string_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr | None) -> str | None:
        if value is None:
            return None
        return value.strip().lower()


class AdminCompanyListItem(BaseModel):
    id: UUID
    name: str
    business_type: str | None
    status: CompanyStatus
    created_at: datetime
    owner_name: str | None
    owner_email: str | None


class RoleCounts(BaseModel):
    owners: int = 0
    company_managers: int = 0
    marketing_managers: int = 0
    employees: int = 0


class AdminCompanyDetail(CompanyRead):
    counts: RoleCounts = Field(default_factory=RoleCounts)


class ProvisionedOwner(BaseModel):
    id: UUID
    email: str
    first_name: str
    last_name: str
    phone: str | None
    status: UserStatus
    linked_existing_user: bool


class AdminCompanyCreated(BaseModel):
    company: CompanyRead
    owner: ProvisionedOwner


class MembershipCreate(BaseModel):
    user_id: UUID
    company_id: UUID
    role: UserRole
    status: MembershipStatus = MembershipStatus.ACTIVE

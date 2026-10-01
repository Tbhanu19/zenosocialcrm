"""Public user schemas. Password fields are intentionally absent."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.permissions import MembershipStatus, UserRole, UserStatus
from app.core.phone import UsPhone


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    status: UserStatus = UserStatus.ACTIVE
    is_super_admin: bool = False

    @field_validator("first_name", "last_name")
    @classmethod
    def strip_required_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Name is required.")
        return cleaned

    def normalized_email(self) -> str:
        return str(self.email).strip().lower()


class MemberListStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    INVITED = "invited"


class CompanyMemberCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    phone: UsPhone = Field(default=None, max_length=30)
    role: UserRole
    membership_status: MembershipStatus = MembershipStatus.ACTIVE

    @field_validator("first_name", "last_name")
    @classmethod
    def strip_required_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Name is required.")
        return cleaned

    def normalized_email(self) -> str:
        return str(self.email).strip().lower()


class CompanyMemberUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: UsPhone = Field(default=None, max_length=30)
    role: UserRole | None = None
    membership_status: MembershipStatus | None = None

    @field_validator("first_name", "last_name")
    @classmethod
    def strip_optional_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Name is required.")
        return cleaned


class CompanyMemberRead(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    email: str
    phone: str | None
    role: UserRole
    membership_status: MembershipStatus
    user_status: UserStatus
    created_at: datetime


class AdminUserRow(CompanyMemberRead):
    company_id: UUID
    company_name: str


class ProfileUpdate(BaseModel):
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


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    phone: str | None
    status: UserStatus
    is_super_admin: bool
    created_at: datetime
    updated_at: datetime

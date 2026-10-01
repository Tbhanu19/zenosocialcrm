"""Pipeline request and response schemas. Company id comes from the path."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.core.permissions import (
    LeadSource,
    LeadStatus,
    PipelineStatus,
    PreferredContactType,
    StageColor,
    StageStatus,
)


class PipelineCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: PipelineStatus = PipelineStatus.ACTIVE

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Name is required.")
        return cleaned

    @field_validator("description")
    @classmethod
    def empty_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class PipelineUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: PipelineStatus | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Name is required.")
        return cleaned

    @field_validator("description")
    @classmethod
    def empty_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class StageCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=5000)
    color: StageColor = StageColor.COPPER
    status: StageStatus = StageStatus.ACTIVE

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Name is required.")
        return cleaned

    @field_validator("description")
    @classmethod
    def empty_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class StageUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=5000)
    color: StageColor | None = None
    status: StageStatus | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Name is required.")
        return cleaned

    @field_validator("description")
    @classmethod
    def empty_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class StageReorder(BaseModel):
    stage_ids: list[UUID] = Field(min_length=1)


class LeadPipelineUpdate(BaseModel):
    pipeline_id: UUID
    pipeline_stage_id: UUID
    expected_pipeline_stage_id: UUID | None = None


class PipelineListItem(BaseModel):
    id: UUID
    name: str
    status: PipelineStatus
    created_at: datetime


class StageRead(BaseModel):
    id: UUID
    pipeline_id: UUID
    name: str
    description: str | None
    position: int
    color: StageColor
    status: StageStatus


class PipelineRead(PipelineListItem):
    description: str | None
    updated_at: datetime
    stages: list[StageRead]


class PipelineCard(BaseModel):
    id: UUID
    title: str
    contact_name: str | None
    estimated_value: str | None
    assignee_name: str | None
    source: LeadSource
    expected_close_date: date | None
    pipeline_stage_id: UUID
    preferred_contact_type: PreferredContactType | None = None
    pipeline_created_at: datetime | None = None


class StageColumn(BaseModel):
    stage_id: UUID
    stage_name: str
    position: int
    color: StageColor
    lead_count: int
    estimated_value_total: str
    leads: list[PipelineCard]
    has_more: bool


class PipelineBoard(BaseModel):
    pipeline_id: UUID
    pipeline_name: str
    per_stage: int
    stages: list[StageColumn]


class LeadPipelineRead(BaseModel):
    id: UUID
    title: str
    status: LeadStatus
    pipeline_id: UUID
    pipeline_stage_id: UUID
    pipeline_name: str
    stage_name: str

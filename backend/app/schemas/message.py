"""Message request and response schemas. Status is assigned by the server."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.core.permissions import MessageDirection, MessageStatus, MessageType


class MessageCreate(BaseModel):
    contact_id: UUID
    message_type: MessageType
    subject: str | None = Field(default=None, max_length=200)
    body: str = Field(min_length=1, max_length=5000)
    deliver: bool = False

    @field_validator("subject")
    @classmethod
    def empty_subject_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("body")
    @classmethod
    def body_must_contain_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Message is required.")
        return cleaned


class MessageUpdate(BaseModel):
    subject: str | None = Field(default=None, max_length=200)
    body: str | None = Field(default=None, min_length=1, max_length=5000)

    @field_validator("subject")
    @classmethod
    def empty_subject_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("body")
    @classmethod
    def strip_body(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Message is required.")
        return cleaned


class MessageListItem(BaseModel):
    id: UUID
    contact_id: UUID | None
    contact_name: str | None
    message_type: MessageType
    direction: MessageDirection
    subject: str | None
    body: str
    status: MessageStatus
    created_by_user_id: UUID | None
    creator_name: str | None
    created_at: datetime


class MessageRead(MessageListItem):
    contact_email: str | None
    contact_phone: str | None
    provider: str | None
    provider_message_id: str | None
    error_message: str | None
    sent_at: datetime | None
    updated_at: datetime


class MessageCreated(BaseModel):
    message: MessageRead
    provider_status: str

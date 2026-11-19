"""Pydantic request/response schemas."""
from datetime import datetime, timezone
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

# Database stores naive UTC; attach the UTC zone so JSON looks like "2026-11-18T22:48:00Z"
UTCDateTime = Annotated[
    datetime,
    AfterValidator(lambda v: v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v),
]


class MeetingCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(None, max_length=5000)


class MeetingFileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    original_filename: str
    file_type: str
    size_bytes: int
    uploaded_at: UTCDateTime


class MeetingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str | None
    duration: float | None
    status: str
    summary: str | None
    created_at: UTCDateTime
    updated_at: UTCDateTime


class MeetingDetail(MeetingOut):
    files: list[MeetingFileOut] = []


class UploadResult(BaseModel):
    meeting_id: str
    uploaded: list[MeetingFileOut]

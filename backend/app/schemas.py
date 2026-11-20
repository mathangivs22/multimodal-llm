"""Pydantic request/response schemas.

CHANGED ON feature/analysis (merging feature/phase-2-llms):
- Removed feature/analysis's own AnalyzeAccepted (the one below, from phase 2, is kept).
- MeetingDetail.latest_job: the newest analysis job, so the meeting and results pages can
  show the current step and why an analysis failed. Filled in by GET /api/meetings/{id}.
"""
from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

# Database stores naive UTC; attach the UTC zone so JSON looks like "2026-11-18T22:48:00Z"
UTCDateTime = Annotated[
    datetime,
    AfterValidator(lambda v: v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v),
]


class MeetingCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(None, max_length=5000)


class MeetingStatusUpdate(BaseModel):
    status: Literal["created", "uploaded", "processing", "completed", "failed"]


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
    latest_job: "JobOut | None" = None  # newest analysis_jobs row, see GET /api/meetings/{id}


class UploadResult(BaseModel):
    meeting_id: str
    uploaded: list[MeetingFileOut]


# ---------------------------------------------------------------------------
# Phase 2: analysis results
# ---------------------------------------------------------------------------
from datetime import date  # noqa: E402


class AnalyzeAccepted(BaseModel):
    meeting_id: str
    status: str


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    stage: str | None
    error_message: str | None
    started_at: UTCDateTime
    finished_at: UTCDateTime | None


class SegmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    seq: int
    meeting_file_id: str
    start_sec: float
    end_sec: float
    text: str


class VisualOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slide_title: str | None
    components: list | None
    relationships: list | None
    workflow_steps: list | None
    uncertain_relationships: list | None
    model_name: str


class SlideOut(BaseModel):
    id: str
    slide_number: int
    title: str | None
    body_text: str | None
    speaker_notes: str | None
    image_url: str | None
    visual: VisualOut | None


class MinutesOut(BaseModel):
    overview: dict | None
    discussion_summary: list | None
    pending_items: list | None
    next_meeting: str | None
    model_name: str
    created_at: UTCDateTime


class DecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    text: str
    kind: str
    source_seq: int | None


class ActionItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    task: str
    owner: str | None
    deadline_text: str | None
    deadline_date: date | None
    status: str
    source_seq: int | None


class ResultsOut(BaseModel):
    meeting_id: str
    status: str
    duration: float | None
    latest_job: JobOut | None
    transcript: list[SegmentOut]
    slides: list[SlideOut]
    minutes: MinutesOut | None
    decisions: list[DecisionOut]
    action_items: list[ActionItemOut]


# MeetingDetail refers to JobOut, which is defined further down
MeetingDetail.model_rebuild()


class MeetingListItem(MeetingOut):
    """A row on the meetings page: the meeting plus a summary of its files."""
    file_count: int = 0
    file_types: list[str] = []  # distinct types, in the order they were uploaded

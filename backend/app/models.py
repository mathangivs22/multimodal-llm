"""SQLAlchemy models.

Phase 1: meetings, meeting_files.
Phase 2: analysis_jobs, transcript_segments, slides, slide_visuals,
         meeting_minutes, decisions, action_items.
"""
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON, BigInteger, CheckConstraint, Date, DateTime, Float, ForeignKey, Index,
    Integer, String, Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    # Naive UTC: MySQL DATETIME cannot store a time zone, so we always store UTC
    # and mark it as UTC when serializing (see UTCDateTime in schemas.py).
    return datetime.now(timezone.utc).replace(tzinfo=None)


MEETING_STATUSES = ("created", "uploaded", "processing", "completed", "failed")
FILE_TYPES = ("audio", "video", "presentation")


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    duration: Mapped[float | None] = mapped_column(Float)  # seconds; filled after transcription
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="created")
    summary: Mapped[str | None] = mapped_column(Text)       # filled by the reasoning engine
    created_at: Mapped[datetime] = mapped_column(DateTime(), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(), default=_now, onupdate=_now, nullable=False
    )

    files: Mapped[list["MeetingFile"]] = relationship(
        back_populates="meeting",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="MeetingFile.uploaded_at",
    )

    __table_args__ = (
        CheckConstraint(f"status IN {MEETING_STATUSES}", name="ck_meetings_status"),
        Index("ix_meetings_created_at", "created_at"),
    )


class MeetingFile(Base):
    __tablename__ = "meeting_files"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    meeting_id: Mapped[str] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)  # relative to backend/
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(), default=_now, nullable=False)

    meeting: Mapped[Meeting] = relationship(back_populates="files")

    __table_args__ = (
        CheckConstraint(f"file_type IN {FILE_TYPES}", name="ck_meeting_files_type"),
        Index("ix_meeting_files_meeting_id", "meeting_id"),
    )


# ---------------------------------------------------------------------------
# Phase 2: analysis results
# ---------------------------------------------------------------------------

JOB_STATUSES = ("running", "completed", "failed")
DECISION_KINDS = ("finalized", "suggested")
ACTION_STATUSES = ("open", "done")


class AnalysisJob(Base):
    """One row per run of the Analyze button."""
    __tablename__ = "analysis_jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    meeting_id: Mapped[str] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    stage: Mapped[str | None] = mapped_column(String(40))   # transcribing, slides, vision, minutes...
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(), default=_now, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime())

    __table_args__ = (
        CheckConstraint(f"status IN {JOB_STATUSES}", name="ck_analysis_jobs_status"),
        Index("ix_analysis_jobs_meeting_id", "meeting_id"),
    )


class TranscriptSegment(Base):
    """A timestamped piece of speech from Whisper. seq is unique within a meeting."""
    __tablename__ = "transcript_segments"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    meeting_id: Mapped[str] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    meeting_file_id: Mapped[str] = mapped_column(
        ForeignKey("meeting_files.id", ondelete="CASCADE"), nullable=False
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    start_sec: Mapped[float] = mapped_column(Float, nullable=False)
    end_sec: Mapped[float] = mapped_column(Float, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        Index("ix_transcript_segments_meeting_seq", "meeting_id", "seq"),
    )


class Slide(Base):
    """Text and image of one slide in a presentation file."""
    __tablename__ = "slides"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    meeting_id: Mapped[str] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    meeting_file_id: Mapped[str] = mapped_column(
        ForeignKey("meeting_files.id", ondelete="CASCADE"), nullable=False
    )
    slide_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(String(500))
    body_text: Mapped[str | None] = mapped_column(Text)
    speaker_notes: Mapped[str | None] = mapped_column(Text)
    image_path: Mapped[str | None] = mapped_column(String(500))  # relative to backend/

    visual: Mapped["SlideVisual | None"] = relationship(
        back_populates="slide", cascade="all, delete-orphan", passive_deletes=True, uselist=False
    )

    __table_args__ = (
        Index("ix_slides_meeting_id", "meeting_id"),
    )


class SlideVisual(Base):
    """What the vision model reads from a slide's diagram."""
    __tablename__ = "slide_visuals"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    slide_id: Mapped[str] = mapped_column(
        ForeignKey("slides.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    slide_title: Mapped[str | None] = mapped_column(String(500))
    components: Mapped[list | None] = mapped_column(JSON)
    relationships: Mapped[list | None] = mapped_column(JSON)
    workflow_steps: Mapped[list | None] = mapped_column(JSON)
    uncertain_relationships: Mapped[list | None] = mapped_column(JSON)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)

    slide: Mapped[Slide] = relationship(back_populates="visual")


class MeetingMinutes(Base):
    """Structured Minutes of Meeting, one per meeting."""
    __tablename__ = "meeting_minutes"

    meeting_id: Mapped[str] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), primary_key=True
    )
    overview: Mapped[dict | None] = mapped_column(JSON)          # title, date, participants
    discussion_summary: Mapped[list | None] = mapped_column(JSON)
    pending_items: Mapped[list | None] = mapped_column(JSON)
    next_meeting: Mapped[str | None] = mapped_column(String(500))
    raw_json: Mapped[str | None] = mapped_column(Text)            # exact model output, for debugging
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(), default=_now, nullable=False)


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    meeting_id: Mapped[str] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)   # finalized | suggested
    source_seq: Mapped[int | None] = mapped_column(Integer)          # transcript_segments.seq

    __table_args__ = (
        CheckConstraint(f"kind IN {DECISION_KINDS}", name="ck_decisions_kind"),
        Index("ix_decisions_meeting_id", "meeting_id"),
    )


class ActionItem(Base):
    __tablename__ = "action_items"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    meeting_id: Mapped[str] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    task: Mapped[str] = mapped_column(Text, nullable=False)
    owner: Mapped[str | None] = mapped_column(String(200))
    deadline_text: Mapped[str | None] = mapped_column(String(200))  # as written in the transcript
    deadline_date: Mapped[date | None] = mapped_column(Date)        # parsed, null if unclear
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    source_seq: Mapped[int | None] = mapped_column(Integer)

    __table_args__ = (
        CheckConstraint(f"status IN {ACTION_STATUSES}", name="ck_action_items_status"),
        Index("ix_action_items_meeting_id", "meeting_id"),
    )

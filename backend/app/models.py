"""SQLAlchemy models. Phase 1: meetings and meeting_files only."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger, CheckConstraint, DateTime, Float, ForeignKey, Index, String, Text,
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

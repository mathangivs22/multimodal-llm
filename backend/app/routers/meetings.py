"""Meeting and file upload endpoints."""
import logging

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.analysis_schemas import MeetingAnalysis
from app.database import get_db
from app.models import AnalysisJob, Meeting, MeetingFile
from app.schemas import (
    JobOut, MeetingCreate, MeetingDetail, MeetingFileOut, MeetingOut, MeetingStatusUpdate, UploadResult,
)
from app.services import analysis, storage

logger = logging.getLogger("meetingiq.api")
router = APIRouter(prefix="/api/meetings", tags=["meetings"])


def _get_meeting_or_404(db: Session, meeting_id: str) -> Meeting:
    meeting = db.get(Meeting, meeting_id, options=[selectinload(Meeting.files)])
    if meeting is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found.")
    return meeting


@router.post("", response_model=MeetingOut, status_code=status.HTTP_201_CREATED)
def create_meeting(payload: MeetingCreate, db: Session = Depends(get_db)):
    meeting = Meeting(title=payload.title.strip(), description=payload.description)
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    logger.info("Created meeting %s (%s)", meeting.id, meeting.title)
    return meeting


@router.get("", response_model=list[MeetingOut])
def list_meetings(db: Session = Depends(get_db)):
    return db.scalars(select(Meeting).order_by(Meeting.created_at.desc())).all()


@router.get("/{meeting_id}", response_model=MeetingDetail)
def get_meeting(meeting_id: str, db: Session = Depends(get_db)):
    """Meeting, its files, and the newest analysis job (current step, or why it failed)."""
    meeting = _get_meeting_or_404(db, meeting_id)
    job = db.scalars(
        select(AnalysisJob).where(AnalysisJob.meeting_id == meeting_id)
        .order_by(AnalysisJob.started_at.desc()).limit(1)
    ).first()
    detail = MeetingDetail.model_validate(meeting)
    detail.latest_job = JobOut.model_validate(job) if job else None
    return detail


@router.get("/{meeting_id}/analysis", response_model=MeetingAnalysis)
def get_meeting_analysis(meeting_id: str, db: Session = Depends(get_db)):
    """Minutes and conflicts for the results page (built from the database, or from JSON
    files when the meeting has no database results). Only once the meeting is 'completed'."""
    meeting = _get_meeting_or_404(db, meeting_id)
    if meeting.status != "completed":
        raise HTTPException(status.HTTP_409_CONFLICT, _NOT_READY.get(meeting.status, "Analysis isn't complete."))
    return analysis.load_analysis(db, meeting)


_NOT_READY = {
    "created": "This meeting has no files yet, so it hasn't been analyzed.",
    "uploaded": "This meeting hasn't been analyzed yet.",
    "processing": "This meeting is still being analyzed.",
    "failed": "The analysis of this meeting failed.",
}


@router.put("/{meeting_id}/status", response_model=MeetingOut)
def set_meeting_status(meeting_id: str, payload: MeetingStatusUpdate, db: Session = Depends(get_db)):
    """Set a meeting's status by hand, for testing with JSON result files.

    The real pipeline (POST /analyze in routers/analysis.py) sets the status itself.
    Use this only to mark a meeting 'completed' after copying result files into its
    storage folder, when the pipeline isn't run."""
    meeting = db.get(Meeting, meeting_id)
    if meeting is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found.")
    if payload.status in ("processing", "completed") and not meeting.files:
        raise HTTPException(status.HTTP_409_CONFLICT, "Upload files before analyzing this meeting.")
    meeting.status = payload.status
    db.commit()
    db.refresh(meeting)
    logger.info("Meeting %s status -> %s", meeting.id, meeting.status)
    return meeting


@router.post("/{meeting_id}/files", response_model=UploadResult, status_code=status.HTTP_201_CREATED)
async def upload_files(
    meeting_id: str,
    files: list[UploadFile] = File(..., description="Audio/video recordings and PPTX/PDF slides"),
    db: Session = Depends(get_db),
):
    meeting = _get_meeting_or_404(db, meeting_id)
    if meeting.status == "processing":
        raise HTTPException(status.HTTP_409_CONFLICT, "Cannot upload while the meeting is being analyzed.")

    # Validate every extension before writing anything to disk
    typed = [(f, storage.detect_file_type(f.filename or "")) for f in files]

    saved_paths: list[str] = []
    records: list[MeetingFile] = []
    try:
        for upload, file_type in typed:
            stored_name, rel_path, size = await storage.save_upload(meeting_id, upload, file_type)
            saved_paths.append(rel_path)
            records.append(MeetingFile(
                meeting_id=meeting_id,
                original_filename=upload.filename,
                stored_filename=stored_name,
                file_type=file_type,
                file_path=rel_path,
                size_bytes=size,
            ))
        db.add_all(records)
        meeting.status = "uploaded"
        db.commit()
    except Exception:
        # All-or-nothing: roll back DB rows and remove files already written
        db.rollback()
        for path in saved_paths:
            storage.delete_file(path)
        logger.exception("Upload failed for meeting %s", meeting_id)
        raise

    for r in records:
        db.refresh(r)
    return UploadResult(
        meeting_id=meeting_id,
        uploaded=[MeetingFileOut.model_validate(r) for r in records],
    )


@router.delete("/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meeting(meeting_id: str, db: Session = Depends(get_db)):
    """Delete a meeting, its files and all its analysis results."""
    meeting = db.get(Meeting, meeting_id)
    if meeting is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Meeting not found.")
    if meeting.status == "processing":
        raise HTTPException(status.HTTP_409_CONFLICT, "Wait for the analysis to finish before deleting.")

    # Database rows go with the meeting (ON DELETE CASCADE); then the files on disk
    db.delete(meeting)
    db.commit()
    storage.delete_meeting_dir(meeting_id)
    logger.info("Deleted meeting %s", meeting_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

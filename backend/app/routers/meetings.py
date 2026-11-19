"""Meeting and file upload endpoints."""
import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.analysis_schemas import MeetingAnalysis
from app.database import get_db
from app.models import Meeting, MeetingFile
from app.schemas import MeetingCreate, MeetingDetail, MeetingFileOut, MeetingOut, UploadResult
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
    return _get_meeting_or_404(db, meeting_id)


@router.get("/{meeting_id}/analysis", response_model=MeetingAnalysis)
def get_meeting_analysis(meeting_id: str, db: Session = Depends(get_db)):
    """Minutes, transcript, slides and conflicts produced by the analysis pipeline."""
    if db.get(Meeting, meeting_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found.")
    return analysis.load_analysis(meeting_id)


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

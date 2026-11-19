"""Analysis endpoints: start an analysis run and read its results."""
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import BASE_DIR
from app.database import get_db
from app.models import (
    ActionItem, AnalysisJob, Decision, Meeting, MeetingFile, MeetingMinutes, Slide,
    TranscriptSegment,
)
from app.schemas import (
    ActionItemOut, AnalyzeAccepted, DecisionOut, JobOut, MinutesOut, ResultsOut,
    SegmentOut, SlideOut, VisualOut,
)
from app.services.pipeline import run_analysis

router = APIRouter(prefix="/api/meetings", tags=["analysis"])


@router.post("/{meeting_id}/analyze", response_model=AnalyzeAccepted,
             status_code=status.HTTP_202_ACCEPTED)
def start_analysis(meeting_id: str, background: BackgroundTasks, db: Session = Depends(get_db)):
    meeting = db.get(Meeting, meeting_id)
    if meeting is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Meeting not found.")
    if meeting.status == "processing":
        raise HTTPException(status.HTTP_409_CONFLICT, "This meeting is already being analyzed.")
    has_files = db.scalar(select(MeetingFile.id).where(MeetingFile.meeting_id == meeting_id).limit(1))
    if has_files is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Upload at least one file before analyzing.")

    meeting.status = "processing"
    db.commit()
    background.add_task(run_analysis, meeting_id)
    return AnalyzeAccepted(meeting_id=meeting_id, status="processing")


@router.get("/{meeting_id}/results", response_model=ResultsOut)
def get_results(meeting_id: str, db: Session = Depends(get_db)):
    meeting = db.get(Meeting, meeting_id)
    if meeting is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Meeting not found.")

    job = db.scalars(
        select(AnalysisJob).where(AnalysisJob.meeting_id == meeting_id)
        .order_by(AnalysisJob.started_at.desc()).limit(1)
    ).first()

    segments = db.scalars(
        select(TranscriptSegment).where(TranscriptSegment.meeting_id == meeting_id)
        .order_by(TranscriptSegment.seq)
    ).all()

    slides = db.scalars(
        select(Slide).where(Slide.meeting_id == meeting_id).order_by(Slide.meeting_file_id, Slide.slide_number)
    ).all()
    slide_out = []
    for s in slides:
        visual = VisualOut.model_validate(s.visual) if s.visual else None
        slide_out.append(SlideOut(
            id=s.id,
            slide_number=s.slide_number,
            title=s.title,
            body_text=s.body_text,
            speaker_notes=s.speaker_notes,
            image_url=f"/api/meetings/{meeting_id}/slides/{s.id}/image" if s.image_path else None,
            visual=visual,
        ))

    minutes = db.get(MeetingMinutes, meeting_id)
    decisions = db.scalars(select(Decision).where(Decision.meeting_id == meeting_id)).all()
    actions = db.scalars(select(ActionItem).where(ActionItem.meeting_id == meeting_id)).all()

    return ResultsOut(
        meeting_id=meeting_id,
        status=meeting.status,
        duration=meeting.duration,
        latest_job=JobOut.model_validate(job) if job else None,
        transcript=[SegmentOut.model_validate(s) for s in segments],
        slides=slide_out,
        minutes=MinutesOut(
            overview=minutes.overview, discussion_summary=minutes.discussion_summary,
            pending_items=minutes.pending_items, next_meeting=minutes.next_meeting,
            model_name=minutes.model_name, created_at=minutes.created_at,
        ) if minutes else None,
        decisions=[DecisionOut.model_validate(d) for d in decisions],
        action_items=[ActionItemOut.model_validate(a) for a in actions],
    )


@router.get("/{meeting_id}/slides/{slide_id}/image")
def get_slide_image(meeting_id: str, slide_id: str, db: Session = Depends(get_db)):
    slide = db.get(Slide, slide_id)
    if slide is None or slide.meeting_id != meeting_id or not slide.image_path:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Slide image not found.")
    path = (BASE_DIR / slide.image_path).resolve()
    if not path.is_file() or BASE_DIR.resolve() not in path.parents:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Slide image not found.")
    return FileResponse(path, media_type="image/png")

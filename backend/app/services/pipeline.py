"""Analysis pipeline: transcribe -> read slides -> (optional) read diagrams -> minutes.

Runs in a background thread started by POST /api/meetings/{id}/analyze.
Each run replaces the previous results for the meeting.
"""
import json
import logging
from datetime import date, datetime, timezone
from pathlib import Path

from app.config import BASE_DIR, STORAGE_DIR, OLLAMA_MODEL, VISION_ENABLED
from app.database import SessionLocal
from app.models import (
    ActionItem, AnalysisJob, Decision, Meeting, MeetingFile, MeetingMinutes,
    Slide, SlideVisual, TranscriptSegment,
)
from app.services import slides as slide_service
from app.services import transcription
from app.services.llm import LLMError, chat_json_with_retry
from app.services.prompts import MINUTES_PROMPT, SLIDE_VISION_PROMPT

logger = logging.getLogger("meetingiq.pipeline")

AV_TYPES = ("audio", "video")
DATE_FORMATS = ("%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y", "%Y-%m-%d")


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _rel(path: Path) -> str:
    return path.resolve().relative_to(BASE_DIR.resolve()).as_posix()


def _clock(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def _parse_date(text: str | None) -> date | None:
    if not text:
        return None
    cleaned = text.strip().rstrip(".")
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None  # e.g. "November 20" has no year: keep only the text


def _as_list(value) -> list:
    return value if isinstance(value, list) else []


def _as_seq(value, valid: set[int]) -> int | None:
    try:
        seq = int(value)
    except (TypeError, ValueError):
        return None
    return seq if seq in valid else None


def _set_stage(db, job: AnalysisJob, stage: str) -> None:
    job.stage = stage
    db.commit()
    logger.info("Meeting %s: %s", job.meeting_id, stage)


def _clear_previous_results(db, meeting_id: str) -> None:
    for model in (TranscriptSegment, Slide, MeetingMinutes, Decision, ActionItem):
        db.query(model).filter(model.meeting_id == meeting_id).delete(synchronize_session=False)
    db.commit()


def run_analysis(meeting_id: str) -> None:
    db = SessionLocal()
    job = AnalysisJob(meeting_id=meeting_id, status="running", stage="starting")
    try:
        meeting = db.get(Meeting, meeting_id)
        if meeting is None:
            return
        meeting.status = "processing"
        db.add(job)
        db.commit()

        files = db.query(MeetingFile).filter(MeetingFile.meeting_id == meeting_id) \
            .order_by(MeetingFile.uploaded_at).all()
        _clear_previous_results(db, meeting_id)

        # 1. Transcription -------------------------------------------------
        _set_stage(db, job, "transcribing")
        seq = 0
        total_duration = 0.0
        for f in files:
            if f.file_type not in AV_TYPES:
                continue
            segments, duration = transcription.transcribe(BASE_DIR / f.file_path)
            total_duration += duration
            for s in segments:
                seq += 1
                db.add(TranscriptSegment(
                    meeting_id=meeting_id, meeting_file_id=f.id, seq=seq,
                    start_sec=s.start, end_sec=s.end, text=s.text,
                ))
        meeting.duration = total_duration or None
        db.commit()

        # 2. Slides --------------------------------------------------------
        _set_stage(db, job, "reading slides")
        slide_rows: list[tuple[Slide, slide_service.SlideData]] = []
        for f in files:
            if f.file_type != "presentation":
                continue
            out_dir = STORAGE_DIR / meeting_id / "slides" / f.id
            for data in slide_service.extract(BASE_DIR / f.file_path, out_dir):
                row = Slide(
                    meeting_id=meeting_id, meeting_file_id=f.id,
                    slide_number=data.slide_number, title=data.title,
                    body_text=data.body_text, speaker_notes=data.speaker_notes,
                    image_path=_rel(data.image_path) if data.image_path else None,
                )
                db.add(row)
                slide_rows.append((row, data))
        db.commit()

        # 3. Diagram analysis (optional) -----------------------------------
        visuals: list[dict] = []
        if VISION_ENABLED and slide_rows:
            _set_stage(db, job, "reading slide diagrams")
            for row, data in slide_rows:
                if data.image_path is None:
                    continue
                try:
                    result, _raw = chat_json_with_retry(
                        SLIDE_VISION_PROMPT.format(slide_number=row.slide_number),
                        image_paths=[data.image_path],
                    )
                except LLMError as exc:
                    logger.warning("Vision failed for slide %s: %s", row.slide_number, exc)
                    continue
                db.add(SlideVisual(
                    slide_id=row.id,
                    slide_title=result.get("slide_title") or row.title,
                    components=_as_list(result.get("components")),
                    relationships=_as_list(result.get("relationships")),
                    workflow_steps=_as_list(result.get("workflow_steps")),
                    uncertain_relationships=_as_list(result.get("uncertain_relationships")),
                    model_name=OLLAMA_MODEL,
                ))
                visuals.append({"slide_number": row.slide_number, **result})
            db.commit()

        # 4. Minutes of Meeting --------------------------------------------
        _set_stage(db, job, "writing minutes")
        transcript_lines = db.query(TranscriptSegment) \
            .filter(TranscriptSegment.meeting_id == meeting_id) \
            .order_by(TranscriptSegment.seq).all()
        transcript_text = "\n".join(
            f"[{s.seq}] {_clock(s.start_sec)} {s.text}" for s in transcript_lines
        ) or "(no audio or video transcript)"
        slides_text = "\n\n".join(
            f"Slide {row.slide_number}: {row.title or ''}\n{row.body_text or ''}\n"
            f"Speaker notes: {row.speaker_notes or ''}"
            for row, _ in slide_rows
        ) or "(no slides)"
        visuals_text = json.dumps(visuals, indent=2) if visuals else "(none)"

        prompt = MINUTES_PROMPT.format(
            slides=slides_text, visuals=visuals_text, transcript=transcript_text,
        )
        minutes, raw = chat_json_with_retry(prompt)

        valid_seqs = {s.seq for s in transcript_lines}
        overview = minutes.get("meeting_overview") if isinstance(minutes.get("meeting_overview"), dict) else {}
        discussion = [str(x) for x in _as_list(minutes.get("discussion_summary"))]

        db.add(MeetingMinutes(
            meeting_id=meeting_id,
            overview=overview,
            discussion_summary=discussion,
            pending_items=[str(x) for x in _as_list(minutes.get("pending_items"))],
            next_meeting=str(minutes.get("next_meeting") or "")[:500] or None,
            raw_json=raw,
            model_name=OLLAMA_MODEL,
        ))

        for item in _as_list(minutes.get("key_decisions")):
            if not isinstance(item, dict) or not item.get("text"):
                continue
            kind = "finalized" if str(item.get("status", "")).lower() == "finalized" else "suggested"
            db.add(Decision(
                meeting_id=meeting_id, text=str(item["text"]), kind=kind,
                source_seq=_as_seq(item.get("source_seq"), valid_seqs),
            ))

        for item in _as_list(minutes.get("action_items")):
            if not isinstance(item, dict) or not item.get("task"):
                continue
            deadline = item.get("deadline") or None
            db.add(ActionItem(
                meeting_id=meeting_id,
                task=str(item["task"]),
                owner=str(item.get("owner") or "")[:200] or None,
                deadline_text=str(deadline)[:200] if deadline else None,
                deadline_date=_parse_date(deadline),
                status="open",
                source_seq=_as_seq(item.get("source_seq"), valid_seqs),
            ))

        # 5. Finish ---------------------------------------------------------
        meeting.summary = "\n".join(discussion) or None
        meeting.status = "completed"
        job.status = "completed"
        job.stage = "done"
        job.finished_at = _now()
        db.commit()
        logger.info("Analysis completed for meeting %s", meeting_id)

    except Exception as exc:
        logger.exception("Analysis failed for meeting %s", meeting_id)
        db.rollback()
        try:
            meeting = db.get(Meeting, meeting_id)
            if meeting is not None:
                meeting.status = "failed"
            job = db.get(AnalysisJob, job.id) if job.id else None
            if job is None:
                job = AnalysisJob(meeting_id=meeting_id, status="failed", started_at=_now())
                db.add(job)
            job.status = "failed"
            job.error_message = str(exc)[:5000]
            job.finished_at = _now()
            db.commit()
        except Exception:
            logger.exception("Could not record failure for meeting %s", meeting_id)
    finally:
        db.close()

"""Analysis pipeline: transcribe -> read slides -> (optional) read diagrams -> minutes.

Runs in a background thread started by POST /api/meetings/{id}/analyze.
Each run replaces the previous results for the meeting.

CHANGED ON feature/analysis (merging feature/phase-2-llms):
- _clear_previous_results() also deletes the meeting's conflict results
  (ConflictCheck, Conflict; positions go with their conflict), so a re-run never
  shows conflicts from an earlier run. Nothing else in this file was changed.
"""
import json
import logging
import re
from datetime import date, datetime, timezone
from pathlib import Path

from app.config import (
    BASE_DIR, MINUTES_MODEL, STORAGE_DIR, VISION_ENABLED, VISION_IMAGE_MAX_SIDE,
    VISION_MODEL, VISION_NUM_PREDICT,
)
from app.database import SessionLocal
from app.models import (
    ActionItem, AnalysisJob, Conflict, ConflictCheck, ConflictPosition, Decision, Meeting, MeetingFile,
    MeetingMinutes, Slide, SlideVisual, TranscriptSegment,
)
from app.services import slides as slide_service
from app.services import transcription
from app.services.llm import LLMError, chat_json_with_retry
from app.services.images import shrink_image
from app.services.conflicts import detect_conflicts
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


PLACEHOLDER = re.compile(r"\[\s*\d+\s*\]")


def _clean_names(values, spoken_text: str) -> list[str]:
    """Keep names that the transcript really contains; drop transcript numbers like "[1]"."""
    names: list[str] = []
    for v in values if isinstance(values, list) else []:
        name = str(v).strip()
        if not name or PLACEHOLDER.fullmatch(name) or name.lower() not in spoken_text:
            continue
        if name not in names:
            names.append(name)
    return names


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
    for model in (TranscriptSegment, Slide, MeetingMinutes, Decision, ActionItem,
                  ConflictCheck, Conflict):
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
            for index, (row, data) in enumerate(slide_rows, start=1):
                if data.image_path is None:
                    continue
                logger.info("Vision: slide %d of %d", index, len(slide_rows))
                try:
                    small = shrink_image(data.image_path, VISION_IMAGE_MAX_SIDE)
                    result, _raw = chat_json_with_retry(
                        SLIDE_VISION_PROMPT.format(slide_number=row.slide_number),
                        image_paths=[small],
                        model=VISION_MODEL,
                        num_predict=VISION_NUM_PREDICT,
                        label=f"vision slide {row.slide_number}",
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
                    model_name=VISION_MODEL,
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
        logger.info("Minutes: prompt is %d chars", len(prompt))
        minutes, raw = chat_json_with_retry(prompt, model=MINUTES_MODEL, label="minutes")

        line_text = {s.seq: s.text.lower() for s in transcript_lines}
        valid_seqs = set(line_text)
        overview = minutes.get("meeting_overview") if isinstance(minutes.get("meeting_overview"), dict) else {}
        spoken_text = " ".join(s.text for s in transcript_lines).lower()
        if isinstance(overview, dict):
            overview["participants"] = _clean_names(overview.get("participants"), spoken_text)
        discussion = [str(x) for x in _as_list(minutes.get("discussion_summary"))]

        db.add(MeetingMinutes(
            meeting_id=meeting_id,
            overview=overview,
            discussion_summary=discussion,
            pending_items=[str(x) for x in _as_list(minutes.get("pending_items"))],
            next_meeting=str(minutes.get("next_meeting") or "")[:500] or None,
            raw_json=raw,
            model_name=MINUTES_MODEL,
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
            seq = _as_seq(item.get("source_seq"), valid_seqs)
            source = line_text.get(seq, "")
            owner = str(item.get("owner") or "").strip()[:200] or None
            deadline = str(item.get("deadline") or "").strip() or None
            # Keep an owner or deadline only if the cited transcript line actually says it
            if owner and owner.lower() not in spoken_text:
                logger.info("Dropped unsupported owner %r for task %r", owner, item["task"])
                owner = None
            if deadline and deadline.lower() not in source:
                logger.info("Dropped unsupported deadline %r for task %r", deadline, item["task"])
                deadline = None
            db.add(ActionItem(
                meeting_id=meeting_id,
                task=str(item["task"]),
                owner=owner,
                deadline_text=deadline[:200] if deadline else None,
                deadline_date=_parse_date(deadline),
                status="open",
                source_seq=seq,
            ))

        # 4b. Conflicts (optional: a failure here does not fail the analysis) ---
        _set_stage(db, job, "checking conflicts")
        try:
            found = detect_conflicts(
                transcript_lines, slide_rows,
                attendees=(overview.get("participants") or []) if isinstance(overview, dict) else [],
            )
        except Exception as exc:
            logger.warning("Conflict check skipped for meeting %s: %s", meeting_id, exc)
            found = None  # no check row is saved, so the page shows "not checked"

        if found is not None:
            db.add(ConflictCheck(meeting_id=meeting_id, model_name=MINUTES_MODEL))
            slide_id_by_number = {row.slide_number: row.id for row, _ in slide_rows}
            for order, c in enumerate(found):
                conflict = Conflict(
                    meeting_id=meeting_id, sort_order=order, kind=c["kind"],
                    severity=c["severity"], status=c["status"], title=c["title"],
                    description=c["description"], resolution=c["resolution"],
                )
                for pos_order, p in enumerate(c["positions"]):
                    conflict.positions.append(ConflictPosition(
                        sort_order=pos_order,
                        speaker=p["speaker"],
                        statement=p["statement"][:5000],
                        source_seqs=p["segment_ids"] or None,
                        slide_ids=[slide_id_by_number[n] for n in p["slide_numbers"]
                                   if n in slide_id_by_number] or None,
                    ))
                db.add(conflict)

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

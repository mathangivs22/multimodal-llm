"""Build the results page's MeetingAnalysis from the analysis tables.

The pipeline (services/pipeline.py) writes one meeting's results to these tables; this
module reads them back in the shape the results page expects (app/analysis_schemas.py).

    meetings             title (via GET /meetings/{id}), duration
    meeting_minutes      overview {title, date, participants}, discussion_summary,
                         pending_items, next_meeting, created_at
    decisions            text, kind -> status, source_seq -> evidence
    action_items         task, owner, deadline_date / deadline_text, status, source_seq -> evidence
    transcript_segments  seq -> "seg-<seq>", start_sec, end_sec, text, meeting_file_id -> file name
    slides               id, slide_number, title, body_text, speaker_notes
    slide_visuals        components, relationships, workflow_steps, uncertain_relationships
    conflict_checks      whether conflict detection ran at all
    conflicts            kind, severity, status, title, description, resolution
    conflict_positions   speaker, statement, source_seqs -> evidence, slide_ids -> evidence

A meeting has results in the database once its meeting_minutes row exists (the pipeline
writes it last, just before marking the meeting completed).
"""
import logging
from datetime import timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.analysis_schemas import MeetingAnalysis
from app.models import (
    ActionItem, Conflict, ConflictCheck, Decision, Meeting, MeetingMinutes, Slide,
    TranscriptSegment,
)
from app.services.pipeline_adapter import KINDS, SEVERITIES, People, _convert_diagram, _text

logger = logging.getLogger("meetingiq.db_results")

AV_TYPES = ("audio", "video")


def has_db_results(db: Session, meeting_id: str) -> bool:
    return db.get(MeetingMinutes, meeting_id) is not None


def _seg_id(seq: int) -> str:
    return f"seg-{seq}"


def _by_source(rows):
    """Rows have no stored order, so list them in the order they came up in the meeting
    (by their transcript line), and ones without a source last."""
    return sorted(rows, key=lambda r: (r.source_seq is None, r.source_seq or 0, r.id))


def build_analysis_from_db(db: Session, meeting: Meeting) -> MeetingAnalysis:
    """Read one meeting's analysis tables into a validated MeetingAnalysis."""
    minutes = db.get(MeetingMinutes, meeting.id)
    if minutes is None:
        raise LookupError(f"Meeting {meeting.id} has no minutes in the database.")

    # Recording names, to tell segments apart when a meeting has several recordings
    # (each recording's timestamps start again at 0:00)
    av_files = {f.id: f.original_filename for f in meeting.files if f.file_type in AV_TYPES}
    several_recordings = len(av_files) > 1
    deck_order = {f.id: i for i, f in enumerate(meeting.files)}

    # ---- transcript
    segments = db.scalars(
        select(TranscriptSegment).where(TranscriptSegment.meeting_id == meeting.id)
        .order_by(TranscriptSegment.seq)
    ).all()
    transcript = [{
        "id": _seg_id(s.seq),
        "speaker_id": None,  # the pipeline doesn't identify speakers
        "start": s.start_sec,
        "end": s.end_sec,
        "text": s.text.strip(),
        "slide_id": None,    # nor which slide was on screen
        "file_name": av_files.get(s.meeting_file_id) if several_recordings else None,
    } for s in segments if s.text and s.text.strip()]
    segment_ids = {s["id"] for s in transcript}

    def seq_evidence(seqs) -> list[dict]:
        out = []
        for seq in seqs or []:
            if isinstance(seq, int) and _seg_id(seq) in segment_ids:
                out.append({"type": "transcript", "id": _seg_id(seq)})
        return out

    # ---- slides (decks in upload order, then slide number)
    slide_rows = db.scalars(
        select(Slide).where(Slide.meeting_id == meeting.id).options(selectinload(Slide.visual))
    ).all()
    slide_rows = sorted(slide_rows, key=lambda s: (deck_order.get(s.meeting_file_id, 0), s.slide_number))
    slides = []
    for s in slide_rows:
        v = s.visual
        slides.append({
            "id": s.id,
            "number": s.slide_number,
            "title": _text(s.title),
            "text": (s.body_text or "").strip(),
            "speaker_notes": _text(s.speaker_notes),
            "shown_at": [],  # the pipeline doesn't record when each slide was on screen
            # Served by GET /api/meetings/{id}/slides/{slide_id}/image; null if no image was rendered
            "image_url": (f"/api/meetings/{meeting.id}/slides/{s.id}/image" if s.image_path else None),
            "diagram": _convert_diagram({
                "components": v.components, "relationships": v.relationships,
                "workflow_steps": v.workflow_steps, "uncertain_relationships": v.uncertain_relationships,
            }) if v else None,
        })
    slide_ids = {s["id"] for s in slides}

    # ---- minutes: overview is the model's own JSON, so read it defensively
    overview = minutes.overview if isinstance(minutes.overview, dict) else {}
    people = People()
    participants = overview.get("participants")
    for name in participants if isinstance(participants, list) else []:
        if isinstance(name, str):
            people.id_for(name)

    decisions = [{
        "id": f"d{i}",
        "text": d.text.strip(),
        "status": d.kind if d.kind in ("finalized", "suggested") else None,
        "evidence": seq_evidence([d.source_seq]),
    } for i, d in enumerate(_by_source(
        db.scalars(select(Decision).where(Decision.meeting_id == meeting.id)).all()), start=1)
        if d.text and d.text.strip()]

    action_items = [{
        "id": a.id,  # the database id, so the results page can tick it (PATCH /api/action-items/{id})
        "can_update": True,
        "task": a.task.strip(),
        "owner_id": people.id_for(a.owner),
        "due_date": a.deadline_date,
        "due_text": _text(a.deadline_text),
        "status": a.status if a.status in ("open", "done") else "open",
        "evidence": seq_evidence([a.source_seq]),
    } for i, a in enumerate(_by_source(
        db.scalars(select(ActionItem).where(ActionItem.meeting_id == meeting.id)).all()), start=1)
        if a.task and a.task.strip()]

    # ---- conflicts
    checked = db.get(ConflictCheck, meeting.id) is not None
    conflicts = []
    if checked:
        rows = db.scalars(
            select(Conflict).where(Conflict.meeting_id == meeting.id)
            .options(selectinload(Conflict.positions)).order_by(Conflict.sort_order)
        ).all()
        for c in rows:
            positions = [{
                "speaker_id": people.id_for(p.speaker),
                "statement": p.statement.strip(),
                "evidence": seq_evidence(p.source_seqs) + [
                    {"type": "slide", "id": sid} for sid in (p.slide_ids or []) if sid in slide_ids
                ],
            } for p in c.positions if p.statement and p.statement.strip()]
            if c.kind not in KINDS or c.severity not in SEVERITIES or len(positions) < 2:
                logger.warning("Skipping conflict %s: needs a known kind and severity and two sides", c.id)
                continue
            conflicts.append({
                "id": c.id,
                "kind": c.kind,
                "severity": c.severity,
                "status": "resolved" if c.status == "resolved" else "unresolved",
                "title": c.title,
                "description": c.description or "",
                "positions": positions,
                "resolution": _text(c.resolution),
            })

    # ---- what these results can't show
    missing = []
    if not transcript:
        missing.append("transcript")
    else:
        missing.append("speakers")
    if not slides:
        missing.append("slides")
    else:
        missing.append("slide_timing")
    if not any(x["evidence"] for x in decisions + action_items):
        missing.append("evidence")
    if not checked:
        missing.append("conflicts")

    duration = meeting.duration or max((s["end"] for s in transcript), default=0.0)
    discussion = minutes.discussion_summary if isinstance(minutes.discussion_summary, list) else []
    pending = minutes.pending_items if isinstance(minutes.pending_items, list) else []

    return MeetingAnalysis.model_validate({
        "meeting_id": meeting.id,
        "is_sample": False,
        "generated_at": minutes.created_at.replace(tzinfo=timezone.utc),
        "title": _text(overview.get("title")) if isinstance(overview.get("title"), str) else None,
        "date": _text(overview.get("date")) if isinstance(overview.get("date"), str) else None,
        "missing": missing,
        "duration_seconds": float(duration),
        "participants": people.items,
        "summary": {"overview": None, "key_points": [t for t in map(_text, discussion) if t]},
        "decisions": decisions,
        "action_items": action_items,
        "conflicts": conflicts,
        "transcript": transcript,
        "slides": slides,
        "pending_items": [t for t in map(_text, pending) if t],
        "next_meeting": _text(minutes.next_meeting),
    })

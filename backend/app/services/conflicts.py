"""Find conflicts: people disagreeing with each other, and speech that contradicts a slide.

Returns None when the check can't run (no transcript), and a list (possibly empty) when it ran.
"""
import logging

from app.config import MINUTES_MODEL
from app.services.llm import chat_json_with_retry
from app.services.prompts import CONFLICTS_PROMPT

logger = logging.getLogger("meetingiq.conflicts")

KINDS = ("speaker_disagreement", "speech_vs_slide")
SEVERITIES = ("low", "medium", "high")
STATUSES = ("resolved", "unresolved")


def _numbers(values, valid: set[int]) -> list[int]:
    """Keep only the numbers that exist (transcript seq or slide number), in order, without repeats."""
    kept: list[int] = []
    for v in values if isinstance(values, list) else []:
        try:
            n = int(v)
        except (TypeError, ValueError):
            continue
        if n in valid and n not in kept:
            kept.append(n)
    return kept


def _key(text: str) -> str:
    """Normalise a statement so the same sentence written twice compares equal."""
    return " ".join(text.lower().split())


def _distinct(positions: list[dict]) -> list[dict]:
    """Drop positions that repeat an earlier statement, keeping the first one."""
    seen: set[str] = set()
    kept = []
    for p in positions:
        key = _key(p["statement"])
        if key in seen:
            continue
        seen.add(key)
        kept.append(p)
    return kept


def detect_conflicts(transcript_lines, slide_rows) -> list[dict] | None:
    """transcript_lines: TranscriptSegment rows. slide_rows: (Slide, SlideData) pairs."""
    if not transcript_lines:
        return None

    has_slides = bool(slide_rows)
    transcript = "\n".join(f"[{s.seq}] {s.text}" for s in transcript_lines)
    slides = "\n\n".join(
        f"Slide {row.slide_number}: {row.title or ''}\n{row.body_text or ''}"
        for row, _ in slide_rows
    ) or "(no slides)"
    prompt = CONFLICTS_PROMPT.format(transcript=transcript, slides=slides)

    result, _raw = chat_json_with_retry(prompt, model=MINUTES_MODEL, label="conflicts")
    raw_list = result.get("conflicts")
    if not isinstance(raw_list, list):
        raise ValueError("The conflicts reply has no 'conflicts' list.")

    valid_seqs = {s.seq for s in transcript_lines}
    valid_slides = {row.slide_number for row, _ in slide_rows}
    found: list[dict] = []
    for c in raw_list:
        if not isinstance(c, dict):
            continue
        kind = c.get("kind")
        if kind not in KINDS or (kind == "speech_vs_slide" and not has_slides):
            logger.info("Dropped conflict with unsupported kind %r", kind)
            continue
        title = str(c.get("title") or "").strip()
        positions = []
        for p in c.get("positions") if isinstance(c.get("positions"), list) else []:
            if not isinstance(p, dict) or not str(p.get("statement") or "").strip():
                continue
            speaker = str(p.get("speaker") or "").strip() or None
            positions.append({
                "speaker": speaker,
                "statement": str(p["statement"]).strip(),
                "segment_ids": _numbers(p.get("segment_ids"), valid_seqs),
                "slide_numbers": _numbers(p.get("slide_numbers"), valid_slides),
            })
        positions = _distinct(positions)
        if not title or len(positions) < 2:
            logger.info("Dropped conflict %r: needs a title and two different positions", title)
            continue
        severity = c.get("severity") if c.get("severity") in SEVERITIES else "low"
        status = c.get("status") if c.get("status") in STATUSES else "unresolved"
        resolution = str(c.get("resolution") or "").strip() or None
        if status == "resolved" and not resolution:
            status = "unresolved"  # 'resolved' needs to say how
        found.append({
            "kind": kind,
            "severity": severity,
            "status": status,
            "title": title[:500],
            "description": str(c.get("description") or "").strip() or None,
            "resolution": resolution if status == "resolved" else None,
            "positions": positions,
        })
    logger.info("Conflict check found %d conflict(s)", len(found))
    return found

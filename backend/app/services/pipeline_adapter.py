"""Turn the analysis pipeline's raw output files into one MeetingAnalysis.

The pipeline writes these files to storage/meetings/<meeting_id>/ (any subset works):

    transcript.json       Whisper-style transcription: {"text", "duration", "segments": [{id, start, end, text}]}
    slides_text.json      [{slide_number, slide_text: [title, ...lines], speaker_notes}]
    vision_results.json   [{slide_number, slide_title, components, relationships, workflow_steps,
                            uncertain_relationships}]  (only slides with diagrams)
    meeting_minutes.json  {meeting_overview: {title, date, participants}, discussion_summary,
                           key_decisions, action_items: [{task, owner, deadline}], pending_items,
                           next_meeting}
    conflicts.json        {conflicts: [...]}, format in backend/formats/conflicts.schema.json

Whatever these files can't provide (speaker labels, slide timing, conflicts, links from
claims to the transcript) is listed in `missing`, so the results page can say so.
"""
import json
import logging
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from app.analysis_schemas import MeetingAnalysis

logger = logging.getLogger("meetingiq.adapter")

TRANSCRIPT_FILE = "transcript.json"
SLIDES_FILE = "slides_text.json"
VISION_FILE = "vision_results.json"
MINUTES_FILE = "meeting_minutes.json"
CONFLICTS_FILE = "conflicts.json"
PIPELINE_FILES = (TRANSCRIPT_FILE, SLIDES_FILE, VISION_FILE, MINUTES_FILE, CONFLICTS_FILE)


def has_pipeline_output(folder: Path) -> bool:
    return any((folder / name).is_file() for name in PIPELINE_FILES)


def _read(folder: Path, name: str) -> Any | None:
    path = folder / name
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _text(value: Any) -> str | None:
    """Strip strings; turn "" / None into None."""
    if value is None:
        return None
    value = str(value).strip()
    return value or None


# ---------- transcript ----------

def _convert_transcript(raw: dict) -> tuple[list[dict], float]:
    segments = raw.get("segments") or []
    if not segments and _text(raw.get("text")):
        # No segment timings: keep the whole text as one line
        segments = [{"id": 0, "start": 0, "end": raw.get("duration") or 0, "text": raw["text"]}]
    out = []
    for i, seg in enumerate(segments):
        text = _text(seg.get("text"))
        if not text:
            continue
        out.append({
            "id": f"seg-{seg.get('id', i)}",
            "speaker_id": None,  # Whisper doesn't label speakers
            "start": float(seg.get("start") or 0),
            "end": float(seg.get("end") or 0),
            "text": text,
            "slide_id": None,
        })
    duration = raw.get("duration") or (out[-1]["end"] if out else 0)
    return out, float(duration)


# ---------- slides ----------

# A bare stat such as "4", "99.9%" or "2 wk", whose label PowerPoint extracted as a separate line
_NUMBER_LIKE = re.compile(r"^[\d.,%$€£+\-–]+\s*[a-zA-Z%]{0,3}$")


def _clean_slide_lines(lines: list[str], slide_number: int) -> list[str]:
    """Drop the page number and glue split stats back together ("4" + "core services")."""
    lines = [l.strip() for l in lines if l and l.strip()]
    if lines and lines[-1] == str(slide_number):
        lines = lines[:-1]
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        nxt = lines[i + 1] if i + 1 < len(lines) else None
        if _NUMBER_LIKE.match(line) and nxt and not _NUMBER_LIKE.match(nxt) and len(nxt) <= 40:
            out.append(f"{line} {nxt}")
            i += 2
        else:
            out.append(line)
            i += 1
    return out


def _convert_diagram(raw: dict) -> dict:
    return {
        "components": [
            {"name": c["name"], "category": _text(c.get("category"))}
            for c in raw.get("components") or [] if _text(c.get("name"))
        ],
        "relationships": [
            {"source": r["source"], "target": r["target"], "description": _text(r.get("description"))}
            for r in raw.get("relationships") or [] if r.get("source") and r.get("target")
        ],
        "workflow_steps": [s for s in raw.get("workflow_steps") or [] if _text(s)],
        "uncertain": [u for u in raw.get("uncertain_relationships") or [] if _text(u)],
    }


def _convert_slides(raw_slides: list | None, raw_vision: list | None) -> list[dict]:
    slides: dict[int, dict] = {}
    for s in raw_slides or []:
        n = int(s["slide_number"])
        lines = _clean_slide_lines(s.get("slide_text") or [], n)
        slides[n] = {
            "id": f"s{n}",
            "number": n,
            "title": lines[0] if lines else None,
            "text": "\n".join(lines[1:]),
            "speaker_notes": _text(s.get("speaker_notes")),
            "shown_at": [],  # the pipeline doesn't record when each slide was on screen
        }
    for v in raw_vision or []:
        n = int(v["slide_number"])
        slide = slides.setdefault(n, {
            "id": f"s{n}", "number": n, "title": _text(v.get("slide_title")),
            "text": "", "speaker_notes": None, "shown_at": [],
        })
        slide["diagram"] = _convert_diagram(v)
    return [slides[n] for n in sorted(slides)]


# ---------- people ----------

class People:
    """Participants by name. Names from the minutes and the conflicts share one id each."""

    def __init__(self):
        self.items: list[dict] = []
        self._by_name: dict[str, str] = {}

    def id_for(self, name: Any) -> str | None:
        name = _text(name)
        if not name:
            return None
        key = name.lower()
        if key not in self._by_name:
            self._by_name[key] = f"p{len(self.items) + 1}"
            self.items.append({"id": self._by_name[key], "name": name, "role": None})
        return self._by_name[key]


# ---------- minutes ----------

def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _item_text(item: Any) -> str | None:
    """Pending items may be strings or objects; take the most descriptive field."""
    if isinstance(item, dict):
        for key in ("item", "task", "text", "description", "title"):
            if _text(item.get(key)):
                return _text(item[key])
        return _text(json.dumps(item))
    return _text(item)


def _convert_minutes(raw: dict, people: People) -> dict:
    overview = raw.get("meeting_overview") or {}
    for name in overview.get("participants") or []:
        people.id_for(name)

    actions = []
    for i, a in enumerate(raw.get("action_items") or [], start=1):
        task = _text(a.get("task"))
        if not task:
            continue
        deadline = _text(a.get("deadline"))
        due = _parse_date(deadline)
        actions.append({
            "id": f"a{i}",
            "task": task,
            "owner_id": people.id_for(a.get("owner")),
            "due_date": due,
            "due_text": deadline if deadline and not due else None,
        })

    return {
        "title": _text(overview.get("title")),
        "date": _text(overview.get("date")),
        "summary": {
            "overview": _text(raw.get("summary") or raw.get("overview")),
            "key_points": [t for t in map(_text, raw.get("discussion_summary") or []) if t],
        },
        "decisions": [
            {"id": f"d{i}", "text": t}
            for i, t in enumerate(filter(None, map(_text, raw.get("key_decisions") or [])), start=1)
        ],
        "action_items": actions,
        "pending_items": [t for t in map(_item_text, raw.get("pending_items") or []) if t],
        "next_meeting": _text(raw.get("next_meeting")),
    }


# ---------- conflicts ----------

KINDS = {"speaker_disagreement", "speech_vs_slide"}
SEVERITIES = {"low", "medium", "high"}


def _as_ints(values: Any) -> list[int]:
    out = []
    for v in values if isinstance(values, list) else []:
        try:
            out.append(int(v))
        except (TypeError, ValueError):
            continue
    return out


def _convert_conflicts(raw: Any, people: People, segment_ids: set[str], slide_ids: set[str]) -> list[dict]:
    """Map the LLM's conflicts onto the results format. Being LLM output, it is read leniently:
    references to segments or slides that don't exist are dropped, and a conflict that is
    unusable (unknown kind, no title, fewer than two sides) is skipped with a warning."""
    items = raw.get("conflicts") if isinstance(raw, dict) else raw
    out = []
    for i, c in enumerate(items if isinstance(items, list) else [], start=1):
        if not isinstance(c, dict):
            continue
        kind = str(c.get("kind", "")).strip().lower()
        title = _text(c.get("title"))
        positions = []
        for p in c.get("positions") or []:
            if not isinstance(p, dict) or not _text(p.get("statement")):
                continue
            evidence = [
                {"type": "transcript", "id": f"seg-{n}"} for n in _as_ints(p.get("segment_ids"))
                if f"seg-{n}" in segment_ids
            ] + [
                {"type": "slide", "id": f"s{n}"} for n in _as_ints(p.get("slide_numbers"))
                if f"s{n}" in slide_ids
            ]
            positions.append({
                "speaker_id": people.id_for(p.get("speaker")),
                "statement": _text(p["statement"]),
                "evidence": evidence,
            })
        if kind not in KINDS or not title or len(positions) < 2:
            logger.warning("Skipping conflict %s (%r): needs a known kind, a title and two sides", i, title)
            continue
        severity = str(c.get("severity", "")).strip().lower()
        out.append({
            "id": f"c{i}",
            "kind": kind,
            "severity": severity if severity in SEVERITIES else "medium",
            "status": "resolved" if str(c.get("status", "")).strip().lower() == "resolved" else "unresolved",
            "title": title,
            "description": _text(c.get("description")) or "",
            "positions": positions,
            "resolution": _text(c.get("resolution")),
        })
    return out


# ---------- all together ----------

def build_analysis(folder: Path, meeting_id: str) -> MeetingAnalysis:
    """Combine whichever pipeline files exist in `folder` into one validated MeetingAnalysis."""
    raw_transcript = _read(folder, TRANSCRIPT_FILE)
    raw_slides = _read(folder, SLIDES_FILE)
    raw_vision = _read(folder, VISION_FILE)
    raw_minutes = _read(folder, MINUTES_FILE)
    raw_conflicts = _read(folder, CONFLICTS_FILE)
    people = People()

    transcript, duration = _convert_transcript(raw_transcript) if raw_transcript else ([], 0.0)
    slides = _convert_slides(raw_slides, raw_vision)
    minutes = _convert_minutes(raw_minutes, people) if raw_minutes else {"summary": {"key_points": []}}
    conflicts = _convert_conflicts(
        raw_conflicts, people, {s["id"] for s in transcript}, {s["id"] for s in slides},
    ) if raw_conflicts is not None else []

    missing = ["evidence"]  # the minutes don't link decisions back to the transcript yet
    if raw_conflicts is None:
        missing.append("conflicts")  # conflict detection hasn't run (an empty list means none found)
    if not transcript:
        missing.append("transcript")
    elif all(s["speaker_id"] is None for s in transcript):
        missing.append("speakers")
    if not slides:
        missing.append("slides")
    elif not any(s["shown_at"] for s in slides):
        missing.append("slide_timing")
    if not raw_minutes:
        missing.append("minutes")

    newest = max((folder / n).stat().st_mtime for n in PIPELINE_FILES if (folder / n).is_file())
    return MeetingAnalysis.model_validate({
        **minutes,
        "meeting_id": meeting_id,
        "is_sample": False,
        "generated_at": datetime.fromtimestamp(newest, tz=timezone.utc),
        "duration_seconds": duration,
        "participants": people.items,
        "transcript": transcript,
        "slides": slides,
        "conflicts": conflicts,
        "missing": missing,
    })

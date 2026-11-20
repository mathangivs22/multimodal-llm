"""The analysis contract: what the analysis pipeline produces and the results page reads.

The pipeline writes one JSON file per meeting to
    storage/meetings/<meeting_id>/analysis.json
matching MeetingAnalysis below. GET /api/meetings/<meeting_id>/analysis serves it.

Conventions
- Times are seconds from the start of the recording (float).
- Every id is unique within its own list (participants, transcript, slides, ...).
- Claims (decisions, action items, conflicts, topics) carry `evidence`: references to
  transcript segments and/or slides, so the UI can show where each claim came from.
"""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

Seconds = float


class EvidenceRef(BaseModel):
    """Points at the source of a claim: a transcript segment or a slide."""
    type: Literal["transcript", "slide"]
    id: str


class Participant(BaseModel):
    id: str
    name: str
    role: str | None = None


class MeetingSummary(BaseModel):
    overview: str | None = None
    key_points: list[str] = []


class Topic(BaseModel):
    """One agenda item / stretch of discussion, for the minutes."""
    id: str
    title: str
    start: Seconds
    end: Seconds
    summary: str
    evidence: list[EvidenceRef] = []


class Decision(BaseModel):
    id: str
    text: str
    status: Literal["finalized", "suggested"] | None = Field(
        None, description="finalized = the team clearly agreed; suggested = proposed only; null = unknown")
    decided_by: list[str] = Field(default=[], description="Participant ids")
    evidence: list[EvidenceRef] = []


class ActionItem(BaseModel):
    id: str
    task: str
    owner_id: str | None = Field(None, description="Participant id, null if unassigned")
    due_date: date | None = None
    due_text: str | None = Field(None, description="Deadline as spoken, when it isn't a calendar date")
    status: Literal["open", "done"] = "open"
    evidence: list[EvidenceRef] = []


class ConflictPosition(BaseModel):
    """One side of a conflict. speaker_id is null when the position comes from a slide."""
    speaker_id: str | None = None
    statement: str
    evidence: list[EvidenceRef] = []


class Conflict(BaseModel):
    id: str
    kind: Literal["speaker_disagreement", "speech_vs_slide"]
    severity: Literal["low", "medium", "high"]
    status: Literal["resolved", "unresolved"]
    title: str
    description: str
    positions: list[ConflictPosition] = Field(..., min_length=2)
    resolution: str | None = None


class TranscriptSegment(BaseModel):
    id: str
    speaker_id: str | None = Field(None, description="Participant id, null without speaker labels")
    start: Seconds
    end: Seconds
    text: str
    slide_id: str | None = Field(None, description="Slide on screen while this was said")
    file_name: str | None = Field(None, description="Recording it came from, when a meeting has several")


class TimeRange(BaseModel):
    start: Seconds
    end: Seconds


class DiagramComponent(BaseModel):
    name: str
    category: str | None = None


class DiagramRelationship(BaseModel):
    source: str
    target: str
    description: str | None = None


class Diagram(BaseModel):
    """What the vision model read from a diagram on the slide."""
    components: list[DiagramComponent] = []
    relationships: list[DiagramRelationship] = []
    workflow_steps: list[str] = []
    uncertain: list[str] = Field([], description="Things the vision model couldn't tell for sure")


# Parts of the analysis the pipeline may not have produced. The UI says "not available"
# for these instead of implying there was nothing to find (e.g. no conflicts).
MissingPart = Literal["transcript", "speakers", "slides", "slide_timing", "minutes", "conflicts", "evidence"]


class Slide(BaseModel):
    id: str
    number: int
    title: str | None = None
    text: str = Field("", description="Text extracted from the slide")
    speaker_notes: str | None = None
    shown_at: list[TimeRange] = []
    image_url: str | None = Field(None, description="Picture of the slide, when one was rendered")
    diagram: Diagram | None = None


class MeetingAnalysis(BaseModel):
    meeting_id: str
    is_sample: bool = False
    generated_at: datetime
    title: str | None = Field(None, description="Title the analysis found, if any")
    date: str | None = Field(None, description="Meeting date as found, if any")
    missing: list[MissingPart] = []
    duration_seconds: Seconds
    participants: list[Participant]
    summary: MeetingSummary
    topics: list[Topic] = []
    decisions: list[Decision] = []
    action_items: list[ActionItem] = []
    conflicts: list[Conflict] = []
    transcript: list[TranscriptSegment] = []
    slides: list[Slide] = []
    pending_items: list[str] = []
    next_meeting: str | None = None

    @model_validator(mode="after")
    def _check_references(self) -> "MeetingAnalysis":
        """Reject output whose ids point at nothing, so broken links never reach the UI."""
        people = {p.id for p in self.participants}
        segments = {s.id for s in self.transcript}
        slides = {s.id for s in self.slides}
        errors: list[str] = []

        def person(pid: str | None, where: str):
            if pid is not None and pid not in people:
                errors.append(f"{where}: unknown participant '{pid}'")

        def refs(evidence: list[EvidenceRef], where: str):
            for ref in evidence:
                known = segments if ref.type == "transcript" else slides
                if ref.id not in known:
                    errors.append(f"{where}: unknown {ref.type} '{ref.id}'")

        for s in self.transcript:
            person(s.speaker_id, f"transcript {s.id}")
            if s.slide_id is not None and s.slide_id not in slides:
                errors.append(f"transcript {s.id}: unknown slide '{s.slide_id}'")
        for t in self.topics:
            refs(t.evidence, f"topic {t.id}")
        for d in self.decisions:
            for pid in d.decided_by:
                person(pid, f"decision {d.id}")
            refs(d.evidence, f"decision {d.id}")
        for a in self.action_items:
            person(a.owner_id, f"action item {a.id}")
            refs(a.evidence, f"action item {a.id}")
        for c in self.conflicts:
            for p in c.positions:
                person(p.speaker_id, f"conflict {c.id}")
                refs(p.evidence, f"conflict {c.id}")

        if errors:
            raise ValueError("; ".join(errors))
        return self

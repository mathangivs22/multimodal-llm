"""Reading analysis results from the database tables the pipeline writes.

Uses an in-memory SQLite database filled the way services/pipeline.py fills it.
"""
import shutil
from datetime import date, datetime
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import (
    ActionItem, AnalysisJob, Conflict, ConflictCheck, ConflictPosition, Decision, Meeting,
    MeetingFile, MeetingMinutes, Slide, SlideVisual, TranscriptSegment,
)
from app.services import analysis as analysis_service
from app.services.db_results import build_analysis_from_db, has_db_results

FIXTURES = Path(__file__).parent / "fixtures" / "sprint14"


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def _fk(dbapi_connection, _record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _meeting(db, *, recordings=("sprint14.mp3",), with_results=True):
    m = Meeting(title="Sprint 14 planning", status="completed", duration=98.0)
    db.add(m)
    db.flush()
    files = []
    for name in recordings:
        files.append(MeetingFile(meeting_id=m.id, original_filename=name, stored_filename=f"{name}.x",
                                 file_type="audio", file_path=f"storage/{name}", size_bytes=1))
    deck = MeetingFile(meeting_id=m.id, original_filename="deck.pptx", stored_filename="deck.x",
                       file_type="presentation", file_path="storage/deck.pptx", size_bytes=1)
    db.add_all(files + [deck])
    db.flush()
    if not with_results:
        db.commit()
        return m, files, deck, []

    texts = ["Let's start sprint planning.", "Email code is 3 points.", "Ship two-factor login."]
    for i, t in enumerate(texts, start=1):
        db.add(TranscriptSegment(meeting_id=m.id, meeting_file_id=files[(i - 1) % len(files)].id,
                                 seq=i, start_sec=10.0 * i, end_sec=10.0 * i + 5, text=t))
    s1 = Slide(meeting_id=m.id, meeting_file_id=deck.id, slide_number=1, title="Welcome", body_text="Project Atlas")
    s2 = Slide(meeting_id=m.id, meeting_file_id=deck.id, slide_number=2, title=None, body_text="", speaker_notes="  ")
    db.add_all([s1, s2])
    db.flush()
    db.add(SlideVisual(slide_id=s1.id, slide_title="Welcome", components=[{"name": "API gateway", "category": "Component"}],
                       relationships=[], workflow_steps=["CLIENTS", "EDGE"], uncertain_relationships=["Arrows unclear"],
                       model_name="qwen3-vl:4b"))
    db.add(MeetingMinutes(meeting_id=m.id, model_name="qwen2.5:3b",
                          overview={"title": "Sprint 14", "date": "", "participants": ["Marcus", "Dev", 42]},
                          discussion_summary=["Split login into two stories.", ""], pending_items=["PDF export scope"],
                          next_meeting=None, created_at=datetime(2026, 11, 20, 10, 0)))
    db.add_all([
        Decision(meeting_id=m.id, text="Ship two-factor login.", kind="finalized", source_seq=3),
        Decision(meeting_id=m.id, text="Maybe add PDF export.", kind="suggested", source_seq=None),
        Decision(meeting_id=m.id, text="Email code is 3 points.", kind="finalized", source_seq=2),
        ActionItem(meeting_id=m.id, task="Update the board", owner="marcus", deadline_text="November 21, 2026",
                   deadline_date=date(2026, 11, 21), status="open", source_seq=1),
        ActionItem(meeting_id=m.id, task="Book a room", owner="Asha", deadline_text="next Friday",
                   deadline_date=None, status="done", source_seq=99),
    ])
    db.commit()
    return m, files, deck, [s1, s2]


def test_minutes_decisions_and_actions_from_tables(db):
    m, files, deck, slides = _meeting(db)
    assert has_db_results(db, m.id)
    a = build_analysis_from_db(db, m)

    assert not a.is_sample and a.title == "Sprint 14" and a.date is None
    assert a.duration_seconds == 98.0
    assert str(a.generated_at) == "2026-11-20 10:00:00+00:00"
    assert a.summary.key_points == ["Split login into two stories."]  # empty strings dropped
    assert [p.name for p in a.participants] == ["Marcus", "Dev", "Asha"]  # 42 ignored; owner added

    # decisions in meeting order (by transcript line), unsourced last; status from `kind`
    assert [(d.text, d.status) for d in a.decisions] == [
        ("Email code is 3 points.", "finalized"), ("Ship two-factor login.", "finalized"),
        ("Maybe add PDF export.", "suggested")]
    assert [r.id for r in a.decisions[0].evidence] == ["seg-2"]
    assert a.decisions[2].evidence == []

    first, second = a.action_items
    assert first.owner_id == "p1" and str(first.due_date) == "2026-11-21" and first.status == "open"
    assert [r.id for r in first.evidence] == ["seg-1"]
    assert second.due_date is None and second.due_text == "next Friday" and second.status == "done"
    assert second.evidence == []  # source_seq 99 doesn't exist
    assert a.pending_items == ["PDF export scope"] and a.next_meeting is None


def test_transcript_and_slides_from_tables(db):
    m, files, deck, slides = _meeting(db)
    a = build_analysis_from_db(db, m)
    assert [s.id for s in a.transcript] == ["seg-1", "seg-2", "seg-3"]
    assert a.transcript[0].start == 10.0 and a.transcript[0].file_name is None  # one recording
    assert [s.number for s in a.slides] == [1, 2]
    assert a.slides[0].diagram.workflow_steps == ["CLIENTS", "EDGE"] and a.slides[1].diagram is None
    assert a.slides[1].speaker_notes is None
    assert set(a.missing) == {"speakers", "slide_timing", "conflicts"}  # evidence exists now


def test_several_recordings_are_named(db):
    m, *_ = _meeting(db, recordings=("part1.mp3", "part2.mp3"))
    a = build_analysis_from_db(db, m)
    assert [s.file_name for s in a.transcript] == ["part1.mp3", "part2.mp3", "part1.mp3"]


def test_conflicts_from_tables(db):
    m, files, deck, (s1, s2) = _meeting(db)
    db.add(ConflictCheck(meeting_id=m.id, model_name="qwen2.5:3b"))
    good = Conflict(meeting_id=m.id, sort_order=0, kind="speech_vs_slide", severity="high", status="unresolved",
                    title="Onboarding deck in a sprint planning meeting", description="Deck doesn't match.")
    good.positions = [
        ConflictPosition(sort_order=0, speaker=None, statement="Welcome to Project Atlas.", slide_ids=[s1.id, "nope"]),
        ConflictPosition(sort_order=1, speaker="Dev", statement="Let's start sprint planning.", source_seqs=[1, 42]),
    ]
    one_sided = Conflict(meeting_id=m.id, sort_order=1, kind="speaker_disagreement", severity="low",
                         status="resolved", title="Only one side")
    one_sided.positions = [ConflictPosition(sort_order=0, speaker="Marcus", statement="Something")]
    db.add_all([good, one_sided])
    db.commit()

    a = build_analysis_from_db(db, m)
    assert "conflicts" not in a.missing
    [c] = a.conflicts  # the one-sided conflict is skipped
    slide_side, dev_side = c.positions
    assert slide_side.speaker_id is None and [(r.type, r.id) for r in slide_side.evidence] == [("slide", s1.id)]
    assert dev_side.speaker_id == "p2" and [r.id for r in dev_side.evidence] == ["seg-1"]


def test_checked_with_no_conflicts_is_not_missing(db):
    m, *_ = _meeting(db)
    db.add(ConflictCheck(meeting_id=m.id))
    db.commit()
    a = build_analysis_from_db(db, m)
    assert a.conflicts == [] and "conflicts" not in a.missing


def test_deleting_a_meeting_removes_its_results(db):
    m, *_ = _meeting(db)
    db.add(AnalysisJob(meeting_id=m.id, status="completed"))
    db.add(ConflictCheck(meeting_id=m.id))
    db.commit()
    db.delete(m)
    db.commit()
    for model in (MeetingMinutes, Decision, ActionItem, TranscriptSegment, Slide, SlideVisual, ConflictCheck, AnalysisJob):
        assert db.query(model).count() == 0, model.__tablename__


# ---------- which source load_analysis uses ----------

def test_database_comes_before_json_files(db, tmp_path, monkeypatch):
    monkeypatch.setattr(analysis_service, "STORAGE_DIR", tmp_path)
    m, *_ = _meeting(db)
    folder = tmp_path / m.id
    folder.mkdir()
    for f in FIXTURES.glob("*.json"):
        shutil.copy(f, folder / f.name)
    a = analysis_service.load_analysis(db, m)
    assert [d.text for d in a.decisions][0] == "Email code is 3 points."  # from the tables, not the files


def test_json_files_when_no_database_results(db, tmp_path, monkeypatch):
    monkeypatch.setattr(analysis_service, "STORAGE_DIR", tmp_path)
    m, *_ = _meeting(db, with_results=False)
    folder = tmp_path / m.id
    folder.mkdir()
    for f in FIXTURES.glob("*.json"):
        shutil.copy(f, folder / f.name)
    a = analysis_service.load_analysis(db, m)
    assert len(a.decisions) == 6 and a.title == "Sprint Planning Sprint 14"


def test_no_results_anywhere_is_404(db, tmp_path, monkeypatch):
    monkeypatch.setattr(analysis_service, "STORAGE_DIR", tmp_path)
    monkeypatch.setattr(analysis_service, "SERVE_SAMPLE_ANALYSIS", False)
    m, *_ = _meeting(db, with_results=False)
    with pytest.raises(HTTPException) as exc:
        analysis_service.load_analysis(db, m)
    assert exc.value.status_code == 404

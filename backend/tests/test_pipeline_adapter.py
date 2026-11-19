"""Converting the analysis pipeline's raw files into the results-page format.

Run from backend/:  python -m pytest
"""
import json
import shutil
from pathlib import Path

import pytest

from app.services.pipeline_adapter import _clean_slide_lines, build_analysis

FIXTURES = Path(__file__).parent / "fixtures" / "sprint14"


@pytest.fixture
def folder(tmp_path):
    for f in FIXTURES.glob("*.json"):
        shutil.copy(f, tmp_path / f.name)
    return tmp_path


def test_full_pipeline_output(folder):
    a = build_analysis(folder, "m1")

    assert a.meeting_id == "m1" and not a.is_sample
    assert a.title == "Sprint Planning Sprint 14"
    assert a.date is None  # "" in the minutes
    assert round(a.duration_seconds) == 98
    assert set(a.missing) == {"conflicts", "evidence", "speakers", "slide_timing"}

    # transcript: every Whisper segment, no speakers
    assert len(a.transcript) == 12
    assert a.transcript[0].id == "seg-0" and a.transcript[0].text.startswith("Okay, good morning")
    assert all(s.speaker_id is None for s in a.transcript)

    # minutes
    assert [p.name for p in a.participants] == ["Marcus", "Dev"]
    assert len(a.summary.key_points) == 5 and a.summary.overview is None
    assert len(a.decisions) == 6
    [action] = a.action_items
    assert action.task.startswith("Update the board")
    assert action.owner_id is None and action.due_date is None and action.due_text is None
    assert a.pending_items == [] and a.next_meeting is None
    assert a.conflicts == []

    # slides: title split off, page numbers dropped, diagrams attached to slides 3 and 5
    assert [s.number for s in a.slides] == list(range(1, 9))
    assert a.slides[2].title == "High-level architecture"
    assert not a.slides[2].text.endswith("3")
    assert a.slides[0].speaker_notes.startswith("Welcome the new team member")
    assert [s.number for s in a.slides if s.diagram] == [3, 5]
    assert a.slides[2].diagram.workflow_steps == ["CLIENTS", "EDGE", "SERVICES", "DATA", "EXTERNAL"]
    assert len(a.slides[2].diagram.uncertain) == 2


def test_split_stats_are_joined():
    lines = ["Project at a glance", "What we build", "4", "core services", "2 wk", "sprint cycle",
             "99.9%", "uptime target", "3", "environments", "2"]
    assert _clean_slide_lines(lines, 2) == [
        "Project at a glance", "What we build", "4 core services", "2 wk sprint cycle",
        "99.9% uptime target", "3 environments",
    ]


def test_partial_output_only_transcript(folder):
    for name in ("slides_text.json", "vision_results.json", "meeting_minutes.json"):
        (folder / name).unlink()
    a = build_analysis(folder, "m1")
    assert len(a.transcript) == 12 and a.slides == [] and a.decisions == []
    assert {"slides", "minutes", "speakers"} <= set(a.missing)


def test_owner_and_deadline_are_used_when_present(folder):
    path = folder / "meeting_minutes.json"
    minutes = json.loads(path.read_text())
    minutes["action_items"] = [
        {"task": "Update the board", "owner": "marcus", "deadline": "2026-11-28"},
        {"task": "Book the demo room", "owner": "Priya", "deadline": "next Friday"},
    ]
    minutes["pending_items"] = ["Confirm PDF export scope", {"item": "Ask design about icons"}]
    minutes["next_meeting"] = "Sprint 14 review"
    path.write_text(json.dumps(minutes))

    a = build_analysis(folder, "m1")
    first, second = a.action_items
    assert first.owner_id == "p1"  # matches "Marcus" regardless of case
    assert str(first.due_date) == "2026-11-28"
    assert [p.name for p in a.participants] == ["Marcus", "Dev", "Priya"]  # unknown owner is added
    assert second.due_date is None and second.due_text == "next Friday"
    assert a.pending_items == ["Confirm PDF export scope", "Ask design about icons"]
    assert a.next_meeting == "Sprint 14 review"

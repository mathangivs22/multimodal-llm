"""Action items across meetings: listing, ticking, keeping ticks on re-analysis, dates."""
from datetime import date, datetime

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import ActionItem, Meeting, MeetingFile, TranscriptSegment
from app.routers.action_items import list_action_items, update_action_item
from app.schemas import ActionItemUpdate
from app.services.pipeline import _done_task_keys, _parse_date, _task_key


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


def _meeting(db, title, status="completed", created=datetime(2026, 11, 18, 9, 0), items=()):
    m = Meeting(title=title, status=status, created_at=created)
    db.add(m)
    db.flush()
    f = MeetingFile(meeting_id=m.id, original_filename="a.mp3", stored_filename=f"{m.id}.mp3",
                    file_type="audio", file_path="x", size_bytes=1)
    db.add(f)
    db.flush()
    db.add(TranscriptSegment(meeting_id=m.id, meeting_file_id=f.id, seq=1, start_sec=94.0, end_sec=99.0, text="..."))
    for task, owner, due, st, seq in items:
        db.add(ActionItem(meeting_id=m.id, task=task, owner=owner, deadline_date=due,
                          deadline_text=str(due) if due else None, status=st, source_seq=seq))
    db.commit()
    return m


def _all(db, **kw):
    return list_action_items(status_filter=kw.get("status", "all"), owner=kw.get("owner"), db=db)


def test_lists_items_of_completed_meetings_soonest_first(db):
    _meeting(db, "Sprint 14", items=[("Update the board", "Marcus", date(2026, 11, 21), "open", 1),
                                     ("Book a room", None, None, "open", None)])
    _meeting(db, "Design review", items=[("Share mock-ups", "Elena", date(2026, 11, 19), "done", None)])
    _meeting(db, "Still analyzing", status="processing", items=[("Hidden", None, None, "open", None)])

    rows = _all(db)
    assert [r.task for r in rows] == ["Share mock-ups", "Update the board", "Book a room"]  # no-date last
    board = rows[1]
    assert board.meeting_title == "Sprint 14" and board.source_start_sec == 94.0
    assert rows[2].source_start_sec is None


def test_filters_by_status_and_owner(db):
    _meeting(db, "Sprint 14", items=[("A", "Marcus", None, "open", None), ("B", "marcus", None, "done", None),
                                     ("C", "Dev", None, "open", None)])
    assert [r.task for r in _all(db, status="open")] == ["A", "C"]
    assert [r.task for r in _all(db, status="done")] == ["B"]
    assert sorted(r.task for r in _all(db, owner="MARCUS")) == ["A", "B"]  # case-insensitive


def test_tick_and_untick(db):
    m = _meeting(db, "Sprint 14", items=[("Update the board", "Marcus", None, "open", 1)])
    item_id = db.query(ActionItem).one().id
    out = update_action_item(item_id, ActionItemUpdate(status="done"), db=db)
    assert out.status == "done" and out.meeting_id == m.id
    assert db.get(ActionItem, item_id).status == "done"
    assert update_action_item(item_id, ActionItemUpdate(status="open"), db=db).status == "open"


def test_unknown_item_is_404(db):
    with pytest.raises(HTTPException) as exc:
        update_action_item("nope", ActionItemUpdate(status="done"), db=db)
    assert exc.value.status_code == 404


def test_refused_while_meeting_is_analyzed(db):
    _meeting(db, "Busy", status="processing", items=[("Task", None, None, "open", None)])
    item_id = db.query(ActionItem).one().id
    with pytest.raises(HTTPException) as exc:
        update_action_item(item_id, ActionItemUpdate(status="done"), db=db)
    assert exc.value.status_code == 409


def test_done_tasks_are_remembered_by_text(db):
    m = _meeting(db, "Sprint 14", items=[("Update the board.", None, None, "done", None),
                                         ("Book a room", None, None, "open", None)])
    keys = _done_task_keys(db, m.id)
    assert keys == {"update the board"}
    assert _task_key("  UPDATE the  board! ") in keys  # same task, written slightly differently
    assert _task_key("Book a room") not in keys


@pytest.mark.parametrize("text, expected", [
    ("November 20, 2026", date(2026, 11, 20)),
    ("2026-12-02", date(2026, 12, 2)),
    ("November 20th, 2026", date(2026, 11, 20)),
    ("November 25", date(2026, 11, 25)),      # no year: the next one after the meeting
    ("Nov 3rd", date(2027, 11, 3)),           # already passed this year: next year
    ("November 18", date(2026, 11, 18)),      # the meeting day itself counts
    ("next Friday", None),
    ("end of the sprint", None),
    ("", None),
])
def test_parse_date(text, expected):
    assert _parse_date(text, reference=date(2026, 11, 18)) == expected


def test_parse_date_without_reference_keeps_old_behaviour():
    assert _parse_date("November 25") is None
    assert _parse_date("November 25, 2026") == date(2026, 11, 25)

"""Action items across all meetings: list them, and tick them as done.

GET   /api/action-items                every action item of every completed meeting
PATCH /api/action-items/{item_id}      {"status": "done" | "open"}

Only meetings whose analysis is completed are listed: while a meeting is being analyzed,
its old action items are being replaced. Ticks survive a re-analysis when the same task
comes back (services/pipeline.py).
"""
import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, tuple_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ActionItem, Meeting, TranscriptSegment
from app.schemas import ActionItemListItem, ActionItemUpdate

logger = logging.getLogger("meetingiq.action_items")
router = APIRouter(prefix="/api/action-items", tags=["action items"])


def _source_times(db: Session, pairs: set[tuple[str, int]]) -> dict[tuple[str, int], float]:
    """start_sec of each (meeting_id, seq) transcript line, in one query."""
    if not pairs:
        return {}
    rows = db.execute(
        select(TranscriptSegment.meeting_id, TranscriptSegment.seq, TranscriptSegment.start_sec)
        .where(tuple_(TranscriptSegment.meeting_id, TranscriptSegment.seq).in_(list(pairs)))
    ).all()
    return {(m, seq): start for m, seq, start in rows}


def _to_out(item: ActionItem, meeting: Meeting, times: dict) -> ActionItemListItem:
    return ActionItemListItem(
        id=item.id,
        task=item.task,
        owner=item.owner,
        deadline_text=item.deadline_text,
        deadline_date=item.deadline_date,
        status=item.status if item.status in ("open", "done") else "open",
        source_seq=item.source_seq,
        source_start_sec=times.get((item.meeting_id, item.source_seq)),
        meeting_id=meeting.id,
        meeting_title=meeting.title,
        meeting_created_at=meeting.created_at,
    )


@router.get("", response_model=list[ActionItemListItem])
def list_action_items(
    status_filter: Literal["open", "done", "all"] = Query("all", alias="status"),
    owner: str | None = None,
    db: Session = Depends(get_db),
):
    """Action items of completed meetings: dated ones first (soonest first), then the rest."""
    query = (
        select(ActionItem, Meeting)
        .join(Meeting, Meeting.id == ActionItem.meeting_id)
        .where(Meeting.status == "completed")
    )
    if status_filter != "all":
        query = query.where(ActionItem.status == status_filter)
    rows = db.execute(query).all()
    if owner:
        rows = [(a, m) for a, m in rows if (a.owner or "").strip().lower() == owner.strip().lower()]
    rows.sort(key=lambda r: (r[0].deadline_date is None, r[0].deadline_date or r[1].created_at.date(),
                             -r[1].created_at.timestamp(), r[0].task.lower()))
    times = _source_times(db, {(a.meeting_id, a.source_seq) for a, _ in rows if a.source_seq is not None})
    return [_to_out(a, m, times) for a, m in rows]


@router.patch("/{item_id}", response_model=ActionItemListItem)
def update_action_item(item_id: str, payload: ActionItemUpdate, db: Session = Depends(get_db)):
    """Tick an action item as done, or untick it."""
    item = db.get(ActionItem, item_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Action item not found. The meeting may have been analyzed again.")
    meeting = db.get(Meeting, item.meeting_id)
    if meeting is None or meeting.status != "completed":
        raise HTTPException(status.HTTP_409_CONFLICT, "This meeting is being analyzed. Try again when it has finished.")
    item.status = payload.status
    db.commit()
    db.refresh(item)
    logger.info("Action item %s -> %s", item.id, item.status)
    times = _source_times(db, {(item.meeting_id, item.source_seq)} if item.source_seq is not None else set())
    return _to_out(item, meeting, times)

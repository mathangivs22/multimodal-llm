"""Runs an analysis for POST /api/meetings/{id}/analyze.

PLACEHOLDER until feature/phase-2-llms is merged. That branch has the real pipeline
(app/services/pipeline.py: run_analysis), which transcribes, reads the slides and writes
the minutes. This branch has no pipeline, so this runner only checks whether result
files are already in storage/meetings/<id>/ (analysis.json or the pipeline's JSON files):
  - files present -> 'completed'
  - no files      -> 'failed'
When merging, call the real run_analysis from the endpoint and delete this module.
"""
import logging

from app.config import STORAGE_DIR
from app.database import SessionLocal
from app.models import Meeting
from app.services import pipeline_adapter
from app.services.analysis import analysis_path

logger = logging.getLogger("meetingiq.runner")


def run_analysis(meeting_id: str) -> None:
    db = SessionLocal()
    try:
        meeting = db.get(Meeting, meeting_id)
        if meeting is None:
            return
        found = analysis_path(meeting_id).is_file() or pipeline_adapter.has_pipeline_output(
            STORAGE_DIR / meeting_id
        )
        meeting.status = "completed" if found else "failed"
        db.commit()
        logger.info("Meeting %s analysis -> %s", meeting_id, meeting.status)
    except Exception:
        logger.exception("Analysis run failed for meeting %s", meeting_id)
        db.rollback()
        meeting = db.get(Meeting, meeting_id)
        if meeting is not None:
            meeting.status = "failed"
            db.commit()
    finally:
        db.close()

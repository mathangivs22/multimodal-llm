"""Load a meeting's analysis result (see app/analysis_schemas.py for the format)."""
import json
import logging
from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.analysis_schemas import MeetingAnalysis
from app.config import SERVE_SAMPLE_ANALYSIS, STORAGE_DIR
from app.models import Meeting
from app.services import db_results, pipeline_adapter

logger = logging.getLogger("meetingiq.analysis")

ANALYSIS_FILENAME = "analysis.json"
SAMPLE_PATH = Path(__file__).resolve().parent.parent / "sample_data" / "sample_analysis.json"


def analysis_path(meeting_id: str) -> Path:
    """Where the analysis pipeline should write its result for this meeting."""
    return STORAGE_DIR / meeting_id / ANALYSIS_FILENAME


@lru_cache(maxsize=1)
def _sample() -> dict:
    return json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))


def load_analysis(db: Session, meeting: Meeting) -> MeetingAnalysis:
    """Return this meeting's analysis, from the first source that exists:
    1. the database: the tables the analysis pipeline writes (services/db_results.py)
    2. analysis.json in the meeting's storage folder, already in the MeetingAnalysis format
    3. JSON result files in that folder (transcript.json, slides_text.json, ...), converted
    4. sample data, when SERVE_SAMPLE_ANALYSIS is on
    Sources 2-4 are for testing the results page without running the pipeline.
    """
    meeting_id = meeting.id
    if db_results.has_db_results(db, meeting_id):
        try:
            return db_results.build_analysis_from_db(db, meeting)
        except (ValidationError, ValueError, TypeError, LookupError) as exc:
            logger.exception("Could not build the analysis for meeting %s from the database", meeting_id)
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "The analysis results for this meeting couldn't be read. Check the server log.",
            ) from exc

    path = analysis_path(meeting_id)
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            data.update(meeting_id=meeting_id, is_sample=False)
            return MeetingAnalysis.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.error("Invalid analysis file %s: %s", path, exc)
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "The analysis result for this meeting is invalid. Check the server log.",
            ) from exc

    folder = STORAGE_DIR / meeting_id
    if pipeline_adapter.has_pipeline_output(folder):
        try:
            return pipeline_adapter.build_analysis(folder, meeting_id)
        except (json.JSONDecodeError, ValidationError, KeyError, TypeError, ValueError) as exc:
            logger.exception("Could not convert pipeline output in %s", folder)
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "The analysis files for this meeting couldn't be read. Check the server log.",
            ) from exc

    if not SERVE_SAMPLE_ANALYSIS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No analysis results were found for this meeting.")

    data = {**_sample(), "meeting_id": meeting_id, "is_sample": True}
    return MeetingAnalysis.model_validate(data)

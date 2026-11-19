"""Load a meeting's analysis result (see app/analysis_schemas.py for the format)."""
import json
import logging
from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException, status
from pydantic import ValidationError

from app.analysis_schemas import MeetingAnalysis
from app.config import SERVE_SAMPLE_ANALYSIS, STORAGE_DIR

logger = logging.getLogger("meetingiq.analysis")

ANALYSIS_FILENAME = "analysis.json"
SAMPLE_PATH = Path(__file__).resolve().parent.parent / "sample_data" / "sample_analysis.json"


def analysis_path(meeting_id: str) -> Path:
    """Where the analysis pipeline should write its result for this meeting."""
    return STORAGE_DIR / meeting_id / ANALYSIS_FILENAME


@lru_cache(maxsize=1)
def _sample() -> dict:
    return json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))


def load_analysis(meeting_id: str) -> MeetingAnalysis:
    """Return the pipeline's result, or sample data if none exists yet (when enabled)."""
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

    if not SERVE_SAMPLE_ANALYSIS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This meeting hasn't been analyzed yet.")

    data = {**_sample(), "meeting_id": meeting_id, "is_sample": True}
    return MeetingAnalysis.model_validate(data)

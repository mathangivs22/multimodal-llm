"""Local speech-to-text with faster-whisper (no ffmpeg needed: it decodes audio via PyAV)."""
import logging
import threading
from dataclasses import dataclass
from pathlib import Path

from app.config import WHISPER_LANGUAGE, WHISPER_MODEL

logger = logging.getLogger("meetingiq.transcription")

_model = None
_model_lock = threading.Lock()


@dataclass
class Segment:
    start: float
    end: float
    text: str


def _get_model():
    global _model
    with _model_lock:
        if _model is None:
            from faster_whisper import WhisperModel  # imported lazily: heavy dependency
            logger.info("Loading Whisper model '%s'", WHISPER_MODEL)
            _model = WhisperModel(WHISPER_MODEL, device="auto", compute_type="default")
    return _model


def transcribe(path: Path) -> tuple[list[Segment], float]:
    """Return (segments, duration_seconds) for an audio or video file."""
    model = _get_model()
    segments, info = model.transcribe(
        str(path),
        language=WHISPER_LANGUAGE,
        vad_filter=True,        # skip silence
        beam_size=5,
    )
    result = [
        Segment(start=s.start, end=s.end, text=s.text.strip())
        for s in segments
        if s.text and s.text.strip()
    ]
    return result, float(info.duration)

"""Central configuration for the MeetingIQ backend.

CHANGED ON feature/analysis (merging feature/phase-2-llms):
- Both branches added settings at the end of this file; both sets are kept as they were
  (SERVE_SAMPLE_ANALYSIS from feature/analysis, then the Phase 2 Ollama/Whisper settings).
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent          # .../backend
load_dotenv(BASE_DIR / ".env")

STORAGE_DIR = BASE_DIR / "storage" / "meetings"             # uploaded files live here

# MySQL example: mysql+pymysql://meetingiq:password@localhost:3306/meetingiq?charset=utf8mb4
# Falls back to a local SQLite file if DATABASE_URL is not set.
DATABASE_URL = os.getenv("DATABASE_URL") or f"sqlite:///{BASE_DIR / 'meetingiq.db'}"

# Origins allowed to call the API from a browser or web view
CORS_ORIGINS = [
    "http://localhost:5173",      # Vite dev server
    "http://127.0.0.1:5173",
    "http://localhost",           # Android app (Capacitor, androidScheme "http")
    "capacitor://localhost",      # iOS app (Capacitor)
]
# More origins, comma-separated, e.g. a hosted website: CORS_EXTRA_ORIGINS=https://meetingiq.example.com
CORS_ORIGINS += [o.strip() for o in os.getenv("CORS_EXTRA_ORIGINS", "").split(",") if o.strip()]

# Allowed extensions grouped by file type
ALLOWED_EXTENSIONS = {
    "audio": {".mp3", ".wav", ".m4a", ".ogg", ".flac"},
    "video": {".mp4", ".mov", ".mkv", ".webm"},
    "presentation": {".pptx", ".pdf"},
}

# Max upload size per file type, in bytes
MAX_FILE_SIZE = {
    "audio": 200 * 1024 * 1024,         # 200 MB
    "video": 1024 * 1024 * 1024,        # 1 GB
    "presentation": 100 * 1024 * 1024,  # 100 MB
}

CHUNK_SIZE = 1024 * 1024  # stream uploads to disk 1 MB at a time

# For UI work without a pipeline: SERVE_SAMPLE_ANALYSIS=true makes a completed meeting that has
# no results (neither in the database nor as JSON files) return sample data instead of 404. Off by default.
SERVE_SAMPLE_ANALYSIS = os.getenv("SERVE_SAMPLE_ANALYSIS", "false").strip().lower() in ("1", "true", "yes")

# ---------------------------------------------------------------------------
# Phase 2: local analysis (Whisper + Ollama + PowerPoint)
# ---------------------------------------------------------------------------

# Ollama runs locally; the backend must be on the same machine to reach it.
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
# Vision model reads slide diagrams (must support images)
VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "gemma3:4b")
# Text model writes the minutes (should answer directly, without reasoning text)
MINUTES_MODEL = os.getenv("OLLAMA_MINUTES_MODEL", "qwen2.5:3b")
# Cap for one diagram reply; a slide description is much shorter than the minutes
VISION_NUM_PREDICT = int(os.getenv("VISION_NUM_PREDICT", "800"))
# Longest side of a slide image sent to the vision model, in pixels
VISION_IMAGE_MAX_SIDE = int(os.getenv("VISION_IMAGE_MAX_SIDE", "1024"))
# Ollama's default context is small; long transcripts would be silently cut off.
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "16384"))
OLLAMA_TIMEOUT_SEC = int(os.getenv("OLLAMA_TIMEOUT_SEC", "900"))

# faster-whisper model: tiny, base, small, medium, large-v3 ...
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "en") or None  # empty = auto-detect

# Set to false to skip the per-slide diagram analysis
VISION_ENABLED = os.getenv("VISION_ENABLED", "true").lower() == "true"

# Folder for rendered slide images, relative to the storage directory
SLIDE_IMAGE_DIR = STORAGE_DIR

# Max tokens the model may write in one reply (the minutes JSON needs well under this)
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "3000"))

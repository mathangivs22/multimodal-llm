"""Central configuration for the MeetingIQ backend."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent          # .../backend
load_dotenv(BASE_DIR / ".env")

STORAGE_DIR = BASE_DIR / "storage" / "meetings"             # uploaded files live here

# MySQL example: mysql+pymysql://meetingiq:password@localhost:3306/meetingiq?charset=utf8mb4
# Falls back to a local SQLite file if DATABASE_URL is not set.
DATABASE_URL = os.getenv("DATABASE_URL") or f"sqlite:///{BASE_DIR / 'meetingiq.db'}"

# Frontend dev servers allowed to call the API (Vite default is 5173)
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

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


# ---------------------------------------------------------------------------
# Phase 2: local analysis (Whisper + Ollama + PowerPoint)
# ---------------------------------------------------------------------------

# Ollama runs locally; the backend must be on the same machine to reach it.
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3-vl:4b")
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

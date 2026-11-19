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

# For UI work without a pipeline: SERVE_SAMPLE_ANALYSIS=true makes a completed meeting that has
# no result files return sample data instead of 404. Off by default.
SERVE_SAMPLE_ANALYSIS = os.getenv("SERVE_SAMPLE_ANALYSIS", "false").strip().lower() in ("1", "true", "yes")

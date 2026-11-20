"""Local file storage: validation and streaming uploads to disk."""
import logging
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.config import ALLOWED_EXTENSIONS, BASE_DIR, CHUNK_SIZE, MAX_FILE_SIZE, STORAGE_DIR

logger = logging.getLogger("meetingiq.storage")


def detect_file_type(filename: str) -> str:
    """Return 'audio' | 'video' | 'presentation', or raise 415."""
    ext = Path(filename).suffix.lower()
    for file_type, extensions in ALLOWED_EXTENSIONS.items():
        if ext in extensions:
            return file_type
    allowed = sorted(e for exts in ALLOWED_EXTENSIONS.values() for e in exts)
    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail=f"'{filename}' has an unsupported extension. Allowed: {', '.join(allowed)}",
    )


async def save_upload(meeting_id: str, upload: UploadFile, file_type: str) -> tuple[str, str, int]:
    """Stream an upload to storage/meetings/<meeting_id>/.

    Returns (stored_filename, relative_path, size_bytes).
    Deletes the partial file and raises 413 if the size limit is exceeded.
    """
    ext = Path(upload.filename).suffix.lower()
    stored_filename = f"{uuid.uuid4().hex}{ext}"
    meeting_dir = STORAGE_DIR / meeting_id
    meeting_dir.mkdir(parents=True, exist_ok=True)
    dest = meeting_dir / stored_filename

    limit = MAX_FILE_SIZE[file_type]
    size = 0
    try:
        with dest.open("wb") as out:
            while chunk := await upload.read(CHUNK_SIZE):
                size += len(chunk)
                if size > limit:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"'{upload.filename}' exceeds the {limit // (1024 * 1024)} MB limit for {file_type} files.",
                    )
                out.write(chunk)
    except BaseException:
        dest.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()

    if size == 0:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"'{upload.filename}' is empty.")

    rel_path = dest.relative_to(BASE_DIR).as_posix()
    logger.info("Saved %s (%d bytes) as %s", upload.filename, size, rel_path)
    return stored_filename, rel_path, size


def delete_file(rel_path: str) -> None:
    (BASE_DIR / rel_path).unlink(missing_ok=True)


def delete_meeting_dir(meeting_id: str) -> None:
    """Remove every stored file for a meeting (uploads, slide images, extracted files)."""
    import shutil

    root = STORAGE_DIR.resolve()
    target = (STORAGE_DIR / meeting_id).resolve()
    # Only ever delete a folder directly inside the storage root
    if target.parent != root:
        logger.error("Refusing to delete %s: outside the storage folder", target)
        return
    shutil.rmtree(target, ignore_errors=True)

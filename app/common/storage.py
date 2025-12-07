import uuid
from pathlib import Path
from typing import Iterable, Tuple

from fastapi import HTTPException, UploadFile, status

from app.common.config import get_settings

settings = get_settings()


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _validate_upload(file: UploadFile) -> None:
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing filename")
    suffix = Path(file.filename).suffix.lower()
    if settings.allowed_upload_extensions and suffix not in settings.allowed_upload_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported file type: {suffix or 'unknown'}"
        )
    # Peek size
    data = file.file.read()
    if len(data) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File too large")
    file.file.seek(0)


def save_upload_file(file: UploadFile, subdir: str = "") -> Tuple[str, Path]:
    """Persist an uploaded file to local storage with basic validation."""
    _validate_upload(file)
    base = ensure_dir(Path(settings.upload_dir) / subdir)
    suffix = Path(file.filename or "").suffix
    key = f"{uuid.uuid4().hex}{suffix}"
    dest = base / key
    try:
        data = file.file.read()
        with dest.open("wb") as buffer:
            buffer.write(data)
    except Exception as exc:  # pragma: no cover - filesystem failure
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save file") from exc
    finally:
        file.file.close()
    return key, dest


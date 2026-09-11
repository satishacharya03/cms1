import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Set
from fastapi import UploadFile, HTTPException
from app.config import settings

# Max file size allowed: 100 MB
MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024

ALLOWED_EXTENSIONS: Set[str] = {
    # Documents
    "pdf", "docx", "doc", "txt", "md",
    # Datasets
    "csv", "tsv", "json", "nc", "hdf5", "xlsx", "xls", "zip", "tar", "gz",
    # Media
    "jpg", "jpeg", "png", "gif", "webp", "mp4", "mov", "avi", "webm"
}


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename to prevent path traversal and unsafe characters."""
    base = os.path.basename(filename)
    clean = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", base)
    return clean.strip("._") or "file"


def get_storage_root() -> Path:
    """Return the absolute path of the storage root directory."""
    root = Path(settings.STORAGE_ROOT).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def save_file(upload_file: UploadFile, subdir: str) -> str:
    """
    Save an uploaded file under STORAGE_ROOT / subdir / YYYY / MM / safe_name.
    Returns relative path from STORAGE_ROOT (e.g. 'reports/2026/09/uuid_report.pdf').
    Designed with an abstraction layer so it can be swapped with S3 seamlessly.
    """
    if not upload_file.filename:
        raise HTTPException(status_code=400, detail="Filename missing in upload.")

    ext = upload_file.filename.split(".")[-1].lower() if "." in upload_file.filename else ""
    if ext and ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File extension '.{ext}' is not permitted. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    now = datetime.now(timezone.utc)
    year_str = now.strftime("%Y")
    month_str = now.strftime("%m")

    root = get_storage_root()
    target_dir = root / subdir / year_str / month_str
    target_dir.mkdir(parents=True, exist_ok=True)

    clean_name = sanitize_filename(upload_file.filename)
    unique_prefix = uuid.uuid4().hex[:8]
    final_filename = f"{unique_prefix}_{clean_name}"
    target_file = target_dir / final_filename

    # Read and validate size
    size_accumulated = 0
    with open(target_file, "wb") as f:
        while chunk := upload_file.file.read(1024 * 1024):  # 1MB chunks
            size_accumulated += len(chunk)
            if size_accumulated > MAX_FILE_SIZE_BYTES:
                target_file.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=f"File size exceeds maximum allowed limit of {MAX_FILE_SIZE_BYTES // (1024*1024)}MB."
                )
            f.write(chunk)

    relative_path = f"{subdir}/{year_str}/{month_str}/{final_filename}"
    return relative_path


def get_file_path(relative_path: str) -> Path:
    """Return the full absolute Path for a given relative path."""
    clean_rel = relative_path.replace("\\", "/").lstrip("/")
    return (get_storage_root() / clean_rel).resolve()


def file_exists(relative_path: str) -> bool:
    """Check if the given relative file path exists in storage."""
    if not relative_path:
        return False
    path = get_file_path(relative_path)
    return path.is_file()


def delete_file(relative_path: str) -> bool:
    """Safely delete a file from storage."""
    try:
        path = get_file_path(relative_path)
        if path.is_file():
            path.unlink()
            return True
        return False
    except Exception:
        return False

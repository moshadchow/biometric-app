from __future__ import annotations

import base64
import mimetypes
import re
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from core.config import settings


BASE_DIR = Path(__file__).resolve().parents[1]
UPLOAD_ROOT = BASE_DIR / settings.UPLOAD_DIR
IMAGE_MIME_TYPES = {"image/jpeg", "image/png"}


def ensure_upload_root() -> Path:
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    return UPLOAD_ROOT


def sanitize_filename(filename: str | None, fallback: str = "upload") -> str:
    raw_name = Path(filename or fallback).name
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", raw_name).strip("._")
    return cleaned or fallback


def guess_extension(filename: str | None, content_type: str | None) -> str:
    if filename:
        suffix = Path(filename).suffix.lower()
        if suffix:
            return suffix
    if content_type:
        guessed = mimetypes.guess_extension(content_type)
        if guessed:
            return guessed
        if content_type == "image/jpeg":
            return ".jpg"
    return ""


async def save_upload_file(
    upload: UploadFile,
    *,
    namespace: str,
    prefix: str,
    max_bytes: int | None = None,
) -> dict[str, str | int]:
    ensure_upload_root()
    namespace_dir = UPLOAD_ROOT / namespace
    namespace_dir.mkdir(parents=True, exist_ok=True)

    extension = guess_extension(upload.filename, upload.content_type)
    stored_name = f"{prefix}-{uuid4().hex}{extension}"
    destination = namespace_dir / stored_name

    total_bytes = 0
    try:
        with destination.open("wb") as handle:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if max_bytes is not None and total_bytes > max_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Uploaded file exceeds the allowed size limit.",
                    )
                handle.write(chunk)
    except HTTPException:
        if destination.exists():
            destination.unlink(missing_ok=True)
        raise
    except Exception:
        if destination.exists():
            destination.unlink(missing_ok=True)
        raise

    return {
        "stored_path": destination.relative_to(BASE_DIR).as_posix(),
        "original_name": sanitize_filename(upload.filename),
        "content_type": upload.content_type or "application/octet-stream",
        "size_bytes": total_bytes,
    }


def decode_data_url(data_url: str) -> tuple[bytes, str]:
    if not data_url.startswith("data:") or "," not in data_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid data URL payload.",
        )

    header, encoded = data_url.split(",", 1)
    mime_type = header[5:].split(";", 1)[0] or "application/octet-stream"
    try:
        return base64.b64decode(encoded), mime_type
    except Exception as exc:  # pragma: no cover - defensive decode guard
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to decode base64 payload.",
        ) from exc

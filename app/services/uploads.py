from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

from app.config import settings

ALLOWED_MIME = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def _safe_ext(upload: UploadFile) -> str:
    ext = Path(upload.filename or "").suffix.lower()
    if upload.content_type in ALLOWED_MIME:
        return ALLOWED_MIME[upload.content_type]
    if ext in ALLOWED_EXT:
        return ".jpg" if ext == ".jpeg" else ext
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Разрешены только изображения JPG, PNG, WEBP или GIF.",
    )


def save_image(upload: UploadFile | None, *, subdir: str) -> str | None:
    """Validate and save an uploaded image, returning its public static URL."""
    if upload is None or not upload.filename:
        return None

    ext = _safe_ext(upload)
    max_bytes = settings.max_upload_mb * 1024 * 1024
    target_dir: Path = settings.upload_dir / subdir
    target_dir.mkdir(parents=True, exist_ok=True)

    data = bytearray()
    while True:
        chunk = upload.file.read(1024 * 1024)
        if not chunk:
            break
        data.extend(chunk)
        if len(data) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Файл слишком большой. Максимум: {settings.max_upload_mb} МБ.",
            )

    if not data:
        raise HTTPException(status_code=400, detail="Загруженный файл пустой.")

    try:
        from io import BytesIO

        with Image.open(BytesIO(data)) as image:
            image.verify()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=400, detail="Файл не является корректным изображением.")

    filename = f"{uuid4().hex}{ext}"
    target = target_dir / filename
    target.write_bytes(data)

    relative = target.relative_to(settings.upload_dir.parent).as_posix()
    return f"/static/{relative}"

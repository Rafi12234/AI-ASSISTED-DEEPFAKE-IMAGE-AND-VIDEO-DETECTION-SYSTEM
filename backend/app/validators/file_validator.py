import re
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.config import get_settings


settings = get_settings()


ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi"}

ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS


@dataclass
class ValidatedUploadFile:
    original_filename: str
    safe_filename: str
    file_type: str
    mime_type: str
    file_size_bytes: int
    content: bytes


def sanitize_filename(filename: str) -> str:
    """
    Convert user-provided filename into a safe filename.
    Original filename will be stored in DB later, but this safe version
    can be used for object names or display-safe references.
    """
    name = Path(filename).name.strip()

    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is missing.",
        )

    # Remove null bytes and control characters
    name = "".join(ch for ch in name if ch.isprintable() and ch != "\x00")

    # Replace unsafe characters
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)

    # Avoid empty result
    if not name or name in {".", ".."}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename.",
        )

    return name


def get_extension(filename: str) -> str:
    extension = Path(filename).suffix.lower()

    if not extension:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File extension is missing.",
        )

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension: {extension}",
        )

    return extension


def infer_type_from_extension(extension: str) -> str:
    if extension in ALLOWED_IMAGE_EXTENSIONS:
        return "image"

    if extension in ALLOWED_VIDEO_EXTENSIONS:
        return "video"

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsupported file type.",
    )


def detect_mime_from_magic(content: bytes) -> str:
    """
    Detect file type using file signature/magic bytes.
    We do not trust only filename or browser-provided Content-Type.
    """

    if len(content) < 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is too small or corrupted.",
        )

    # JPEG: FF D8 FF
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"

    # PNG: 89 50 4E 47 0D 0A 1A 0A
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"

    # WEBP: RIFF....WEBP
    if content[0:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"

    # AVI: RIFF....AVI
    if content[0:4] == b"RIFF" and content[8:11] == b"AVI":
        return "video/x-msvideo"

    # MP4 / MOV usually have ftyp box at byte 4
    if content[4:8] == b"ftyp":
        brand = content[8:12].lower()

        # Common QuickTime/MOV brands
        if brand in {b"qt  "}:
            return "video/quicktime"

        return "video/mp4"

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="File signature does not match any supported image/video format.",
    )


def validate_extension_matches_mime(extension: str, detected_mime: str) -> None:
    valid_pairs = {
        ".jpg": {"image/jpeg"},
        ".jpeg": {"image/jpeg"},
        ".png": {"image/png"},
        ".webp": {"image/webp"},
        ".mp4": {"video/mp4", "video/quicktime"},
        ".mov": {"video/quicktime", "video/mp4"},
        ".avi": {"video/x-msvideo"},
    }

    allowed_mimes = valid_pairs.get(extension, set())

    if detected_mime not in allowed_mimes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"File extension {extension} does not match detected file type "
                f"{detected_mime}."
            ),
        )


def validate_size(file_type: str, file_size_bytes: int) -> None:
    if file_size_bytes <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    if file_type == "image":
        max_size = settings.max_image_size_mb * 1024 * 1024
        max_label = f"{settings.max_image_size_mb}MB"
    else:
        max_size = settings.max_video_size_mb * 1024 * 1024
        max_label = f"{settings.max_video_size_mb}MB"

    if file_size_bytes > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"{file_type.capitalize()} file is too large. Maximum allowed size is {max_label}.",
        )


async def read_upload_file(upload_file: UploadFile, max_limit_bytes: int) -> bytes:
    """
    Read file safely with a hard size limit.
    This prevents accidentally reading very large files into memory.
    Later, during production optimization, this can be changed to streaming.
    """
    content = await upload_file.read(max_limit_bytes + 1)

    if len(content) > max_limit_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Uploaded file is larger than the allowed limit.",
        )

    return content


async def validate_upload_file(upload_file: UploadFile) -> ValidatedUploadFile:
    if upload_file.filename is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required.",
        )

    original_filename = upload_file.filename
    safe_filename = sanitize_filename(original_filename)
    extension = get_extension(safe_filename)
    file_type = infer_type_from_extension(extension)

    if file_type == "image":
        max_limit_bytes = settings.max_image_size_mb * 1024 * 1024
    else:
        max_limit_bytes = settings.max_video_size_mb * 1024 * 1024

    content = await read_upload_file(upload_file, max_limit_bytes=max_limit_bytes)
    file_size_bytes = len(content)

    validate_size(file_type, file_size_bytes)

    detected_mime = detect_mime_from_magic(content)
    validate_extension_matches_mime(extension, detected_mime)

    return ValidatedUploadFile(
        original_filename=original_filename,
        safe_filename=safe_filename,
        file_type=file_type,
        mime_type=detected_mime,
        file_size_bytes=file_size_bytes,
        content=content,
    )
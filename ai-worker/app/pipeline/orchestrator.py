from __future__ import annotations

import time
from typing import Any

from app.detectors.heuristic_detector import (
    run_image_heuristic_detector,
    run_video_heuristic_detector,
)
from app.pipeline.result_builder import build_pipeline_result, to_legacy_api_response


def detect_media_type(*, mime_type: str, filename: str) -> str:
    lower_mime = (mime_type or "").lower()
    lower_filename = filename.lower()

    if lower_mime.startswith("image/"):
        return "image"

    if lower_mime.startswith("video/"):
        return "video"

    if lower_filename.endswith((".jpg", ".jpeg", ".png", ".webp", ".bmp")):
        return "image"

    if lower_filename.endswith((".mp4", ".mov", ".avi", ".mkv", ".webm")):
        return "video"

    return "unknown"


def analyze_media_bytes(
    *,
    file_bytes: bytes,
    filename: str,
    mime_type: str,
    forced_media_type: str | None = None,
) -> dict[str, Any]:
    started_at = time.perf_counter()

    media_type = forced_media_type or detect_media_type(
        mime_type=mime_type,
        filename=filename,
    )

    if media_type == "image":
        raw_result = run_image_heuristic_detector(
            file_bytes=file_bytes,
            filename=filename,
            mime_type=mime_type,
        )

    elif media_type == "video":
        raw_result = run_video_heuristic_detector(
            file_bytes=file_bytes,
            filename=filename,
            mime_type=mime_type,
        )

    else:
        raise ValueError(
            f"Unsupported media type. filename={filename}, mime_type={mime_type}"
        )

    pipeline_result = build_pipeline_result(
        media_type=media_type,
        raw_result=raw_result,
        started_at=started_at,
    )

    return to_legacy_api_response(pipeline_result)
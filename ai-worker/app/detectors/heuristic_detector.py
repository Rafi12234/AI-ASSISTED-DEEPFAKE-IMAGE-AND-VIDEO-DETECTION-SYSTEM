from __future__ import annotations

from typing import Any

from app.services.image_analyzer import analyze_image_bytes
from app.services.video_analyzer import analyze_video_bytes


def run_image_heuristic_detector(
    *,
    file_bytes: bytes,
    filename: str,
    mime_type: str,
) -> dict[str, Any]:
    return analyze_image_bytes(
        file_bytes=file_bytes,
        filename=filename,
        mime_type=mime_type,
    )


def run_video_heuristic_detector(
    *,
    file_bytes: bytes,
    filename: str,
    mime_type: str,
) -> dict[str, Any]:
    return analyze_video_bytes(
        file_bytes=file_bytes,
        filename=filename,
        mime_type=mime_type,
    )
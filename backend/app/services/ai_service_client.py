from __future__ import annotations

from typing import Any

import httpx

from app.config import settings
from app.services.storage import get_minio_client


def normalize_ai_service_url() -> str:
    return settings.ai_service_url.rstrip("/")


def read_raw_file_from_minio(stored_path: str) -> bytes:
    minio_client = get_minio_client()

    response = minio_client.get_object(
        settings.minio_bucket_raw,
        stored_path,
    )

    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


async def analyze_image_with_ai_service(
    *,
    stored_path: str,
    filename: str,
    mime_type: str,
) -> dict[str, Any]:
    file_bytes = read_raw_file_from_minio(stored_path)

    if not file_bytes:
        raise RuntimeError("Stored file is empty.")

    endpoint = f"{normalize_ai_service_url()}/analyze/image"

    files = {
        "file": (
            filename,
            file_bytes,
            mime_type or "application/octet-stream",
        )
    }

    async with httpx.AsyncClient(timeout=90.0) as client:
        response = await client.post(
            endpoint,
            files=files,
        )

    if response.status_code >= 400:
        raise RuntimeError(
            f"AI service failed with status {response.status_code}: {response.text}"
        )

    data = response.json()

    if "final_score" not in data or "risk_level" not in data:
        raise RuntimeError("AI service response is missing required result fields.")

    return data
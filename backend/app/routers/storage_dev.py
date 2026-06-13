from datetime import datetime, timezone

from fastapi import APIRouter

from app.config import get_settings
from app.services.storage import (
    check_minio_connection,
    ensure_required_buckets,
    get_presigned_get_url,
    object_exists,
    upload_bytes,
)


router = APIRouter(prefix="/dev/storage", tags=["Dev Storage"])
settings = get_settings()


@router.get("/health")
def storage_health():
    ensure_required_buckets()

    return {
        "status": "ok" if check_minio_connection() else "error",
        "buckets": {
            "raw": settings.minio_bucket_raw,
            "processed": settings.minio_bucket_processed,
            "reports": settings.minio_bucket_reports,
        },
    }


@router.post("/test-upload")
def test_upload():
    ensure_required_buckets()

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    object_name = f"dev-tests/test-{timestamp}.txt"

    content = (
        "Deepfake Detection System MinIO test file.\n"
        f"Created at UTC: {timestamp}\n"
    ).encode("utf-8")

    upload_bytes(
        bucket_name=settings.minio_bucket_reports,
        object_name=object_name,
        data=content,
        content_type="text/plain",
    )

    exists = object_exists(
        bucket_name=settings.minio_bucket_reports,
        object_name=object_name,
    )

    presigned_url = get_presigned_get_url(
        bucket_name=settings.minio_bucket_reports,
        object_name=object_name,
        expires_minutes=15,
    )

    return {
        "status": "uploaded",
        "bucket": settings.minio_bucket_reports,
        "object_name": object_name,
        "exists": exists,
        "presigned_url": presigned_url,
        "expires_minutes": 15,
    }
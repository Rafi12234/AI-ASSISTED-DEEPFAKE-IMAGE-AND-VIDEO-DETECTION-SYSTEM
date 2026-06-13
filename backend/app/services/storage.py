from datetime import timedelta
from io import BytesIO
from typing import BinaryIO

from minio import Minio
from minio.error import S3Error

from app.config import get_settings


settings = get_settings()


def get_minio_client() -> Minio:
    return Minio(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=False,
    )


def get_required_buckets() -> list[str]:
    return [
        settings.minio_bucket_raw,
        settings.minio_bucket_processed,
        settings.minio_bucket_reports,
    ]


def ensure_bucket_exists(bucket_name: str) -> None:
    client = get_minio_client()

    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)


def ensure_required_buckets() -> None:
    for bucket_name in get_required_buckets():
        ensure_bucket_exists(bucket_name)


def check_minio_connection() -> bool:
    try:
        client = get_minio_client()
        client.list_buckets()
        return True
    except Exception:
        return False


def upload_bytes(
    *,
    bucket_name: str,
    object_name: str,
    data: bytes,
    content_type: str = "application/octet-stream",
) -> str:
    ensure_bucket_exists(bucket_name)

    client = get_minio_client()

    client.put_object(
        bucket_name=bucket_name,
        object_name=object_name,
        data=BytesIO(data),
        length=len(data),
        content_type=content_type,
    )

    return object_name


def upload_file_object(
    *,
    bucket_name: str,
    object_name: str,
    file_obj: BinaryIO,
    length: int,
    content_type: str = "application/octet-stream",
) -> str:
    ensure_bucket_exists(bucket_name)

    client = get_minio_client()

    client.put_object(
        bucket_name=bucket_name,
        object_name=object_name,
        data=file_obj,
        length=length,
        content_type=content_type,
    )

    return object_name


def get_presigned_get_url(
    *,
    bucket_name: str,
    object_name: str,
    expires_minutes: int = 15,
) -> str:
    client = get_minio_client()

    return client.presigned_get_object(
        bucket_name=bucket_name,
        object_name=object_name,
        expires=timedelta(minutes=expires_minutes),
    )


def object_exists(
    *,
    bucket_name: str,
    object_name: str,
) -> bool:
    client = get_minio_client()

    try:
        client.stat_object(bucket_name, object_name)
        return True
    except S3Error:
        return False


def delete_object(
    *,
    bucket_name: str,
    object_name: str,
) -> None:
    client = get_minio_client()
    client.remove_object(bucket_name, object_name)
from minio import Minio

from app.config import get_settings


settings = get_settings()


def get_minio_client() -> Minio:
    return Minio(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=False,
    )


def check_minio_connection() -> bool:
    try:
        client = get_minio_client()
        client.list_buckets()
        return True
    except Exception:
        return False
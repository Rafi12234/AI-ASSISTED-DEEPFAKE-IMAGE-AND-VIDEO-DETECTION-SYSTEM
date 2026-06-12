from fastapi import APIRouter

from app.config import get_settings
from app.database import check_database_connection
from app.services.cache import check_redis_connection
from app.services.storage import check_minio_connection


router = APIRouter()
settings = get_settings()


@router.get("/health")
async def health_check():
    database_ok = await check_database_connection()
    redis_ok = await check_redis_connection()
    minio_ok = check_minio_connection()

    services = {
        "api": "ok",
        "database": "ok" if database_ok else "error",
        "redis": "ok" if redis_ok else "error",
        "minio": "ok" if minio_ok else "error",
    }

    overall_status = "ok" if all(value == "ok" for value in services.values()) else "degraded"

    return {
        "status": overall_status,
        "app": settings.app_name,
        "environment": settings.app_env,
        "services": services,
    }
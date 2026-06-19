from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter
from sqlalchemy import text

from app.config import settings
from app.database import AsyncSessionLocal
from app.services.cache import check_redis_connection
from app.services.storage import check_minio_connection


router = APIRouter(prefix="/system", tags=["System"])


async def check_database() -> dict[str, Any]:
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(text("SELECT 1 AS ok"))
            row = result.first()

        return {
            "status": "ok" if row and row.ok == 1 else "error",
            "message": "Database connection successful.",
        }
    except Exception as exc:
        return {
            "status": "error",
            "message": str(exc),
        }


async def check_redis() -> dict[str, Any]:
    try:
        is_ok = await check_redis_connection()

        return {
            "status": "ok" if is_ok else "error",
            "message": "Redis connection successful." if is_ok else "Redis connection failed.",
        }
    except Exception as exc:
        return {
            "status": "error",
            "message": str(exc),
        }


def check_minio() -> dict[str, Any]:
    try:
        is_ok = check_minio_connection()

        return {
            "status": "ok" if is_ok else "error",
            "message": "MinIO connection successful." if is_ok else "MinIO connection failed.",
        }
    except Exception as exc:
        return {
            "status": "error",
            "message": str(exc),
        }


async def check_ai_service() -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{settings.ai_service_url.rstrip('/')}/health")

        if response.status_code != 200:
            return {
                "status": "error",
                "message": f"AI service returned HTTP {response.status_code}.",
            }

        data = response.json()

        return {
            "status": data.get("status", "ok"),
            "message": "AI service connection successful.",
            "engine": data.get("engine"),
            "supported_media": data.get("supported_media", []),
            "raw": data,
        }
    except Exception as exc:
        return {
            "status": "error",
            "message": str(exc),
        }


@router.get("/health")
async def get_system_health():
    database = await check_database()
    redis = await check_redis()
    minio = check_minio()
    ai_service = await check_ai_service()

    services = {
        "backend_api": {
            "status": "ok",
            "message": "Backend API is running.",
        },
        "database": database,
        "redis": redis,
        "minio": minio,
        "ai_service": ai_service,
    }

    overall_status = "ok"

    for service in services.values():
        if service.get("status") != "ok":
            overall_status = "degraded"
            break

    return {
        "status": overall_status,
        "services": services,
    }
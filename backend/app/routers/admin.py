import uuid
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.core import User


router = APIRouter(prefix="/admin", tags=["Admin"])


def make_json_safe(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, uuid.UUID):
        return str(value)

    if isinstance(value, dict):
        return {key: make_json_safe(item) for key, item in value.items()}

    if isinstance(value, list):
        return [make_json_safe(item) for item in value]

    return value


def row_to_dict(row: Any) -> dict[str, Any]:
    return {
        key: make_json_safe(value)
        for key, value in row._mapping.items()
    }


def require_admin(current_user: User) -> None:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )


@router.get("/overview")
async def get_admin_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    uploads_result = await db.execute(
        text(
            """
            SELECT COUNT(*) AS total_uploads
            FROM media_uploads
            WHERE is_deleted = false
            """
        )
    )

    jobs_result = await db.execute(
        text(
            """
            SELECT
                COUNT(*) AS total_jobs,
                COUNT(*) FILTER (WHERE status = 'queued') AS queued_jobs,
                COUNT(*) FILTER (WHERE status = 'processing') AS processing_jobs,
                COUNT(*) FILTER (WHERE status = 'completed') AS completed_jobs,
                COUNT(*) FILTER (WHERE status = 'failed') AS failed_jobs
            FROM analysis_jobs
            """
        )
    )

    results_result = await db.execute(
        text(
            """
            SELECT
                COUNT(*) AS total_results,
                COUNT(*) FILTER (WHERE risk_level = 'likely_authentic') AS likely_authentic_count,
                COUNT(*) FILTER (WHERE risk_level = 'uncertain') AS uncertain_count,
                COUNT(*) FILTER (WHERE risk_level = 'suspicious') AS suspicious_count,
                COUNT(*) FILTER (WHERE risk_level = 'high_risk') AS high_risk_count
            FROM analysis_results
            """
        )
    )

    return {
        "uploads": row_to_dict(uploads_result.first()),
        "jobs": row_to_dict(jobs_result.first()),
        "results": row_to_dict(results_result.first()),
    }


@router.get("/jobs")
async def list_admin_jobs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    result = await db.execute(
        text(
            """
            SELECT
                aj.id AS job_id,
                aj.status AS job_status,
                aj.queued_at,
                aj.started_at,
                aj.completed_at,
                aj.error_message,

                mu.id AS upload_id,
                mu.original_filename,
                mu.file_type,
                mu.mime_type,
                mu.file_size_bytes,
                mu.upload_status,
                mu.created_at AS uploaded_at,

                u.id AS user_id,
                u.email AS user_email,

                ar.id AS result_id,
                ar.final_score,
                ar.risk_level,
                ar.confidence,
                ar.created_at AS result_created_at
            FROM analysis_jobs aj
            INNER JOIN media_uploads mu ON mu.id = aj.media_upload_id
            INNER JOIN users u ON u.id = mu.user_id
            LEFT JOIN analysis_results ar ON ar.analysis_job_id = aj.id
            WHERE mu.is_deleted = false
            ORDER BY aj.queued_at DESC
            LIMIT 100
            """
        )
    )

    return [row_to_dict(row) for row in result.all()]
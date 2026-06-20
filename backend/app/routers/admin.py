import uuid
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.core import User
from app.services.queue import enqueue_analysis_job

router = APIRouter(prefix="/admin", tags=["Admin"])


ALLOWED_JOB_STATUSES = {"queued", "processing", "completed", "failed"}
ALLOWED_RISK_LEVELS = {
    "likely_authentic",
    "uncertain",
    "suspicious",
    "high_risk",
    "not_available",
}
ALLOWED_MEDIA_TYPES = {"image", "video"}


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
    search: str | None = Query(default=None),
    job_status: str | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    media_type: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=300),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    where_clauses = ["mu.is_deleted = false"]
    params: dict[str, Any] = {
        "limit": limit,
    }

    if search:
        cleaned_search = search.strip().lower()

        if cleaned_search:
            where_clauses.append(
                """
                (
                    LOWER(mu.original_filename) LIKE :search
                    OR LOWER(u.email) LIKE :search
                    OR LOWER(CAST(aj.id AS TEXT)) LIKE :search
                    OR LOWER(CAST(mu.id AS TEXT)) LIKE :search
                )
                """
            )
            params["search"] = f"%{cleaned_search}%"

    if job_status and job_status != "all":
        if job_status not in ALLOWED_JOB_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid job status filter.",
            )

        where_clauses.append("aj.status = :job_status")
        params["job_status"] = job_status

    if risk_level and risk_level != "all":
        if risk_level not in ALLOWED_RISK_LEVELS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid risk level filter.",
            )

        if risk_level == "not_available":
            where_clauses.append("ar.risk_level IS NULL")
        else:
            where_clauses.append("ar.risk_level = :risk_level")
            params["risk_level"] = risk_level

    if media_type and media_type != "all":
        if media_type not in ALLOWED_MEDIA_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid media type filter.",
            )

        where_clauses.append("mu.file_type = :media_type")
        params["media_type"] = media_type

    where_sql = " AND ".join(where_clauses)

    result = await db.execute(
        text(
            f"""
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
            WHERE {where_sql}
            ORDER BY aj.queued_at DESC
            LIMIT :limit
            """
        ),
        params,
    )

    return [row_to_dict(row) for row in result.all()]


@router.post("/jobs/{job_id}/retry")
async def retry_admin_job(
    job_id: uuid.UUID,
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

                mu.id AS upload_id,
                mu.user_id,
                mu.file_type,
                mu.stored_path,
                mu.mime_type
            FROM analysis_jobs aj
            INNER JOIN media_uploads mu ON mu.id = aj.media_upload_id
            WHERE aj.id = :job_id
              AND mu.is_deleted = false
            LIMIT 1
            """
        ),
        {
            "job_id": job_id,
        },
    )

    row = result.first()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )

    job = row._mapping

    if job["job_status"] == "processing":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This job is already processing.",
        )

    if job["job_status"] == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This job is already completed. Completed jobs cannot be retried.",
        )

    await db.execute(
        text(
            """
            UPDATE analysis_jobs
            SET
                status = 'queued',
                queued_at = NOW(),
                started_at = NULL,
                completed_at = NULL,
                error_message = NULL
            WHERE id = :job_id
            """
        ),
        {
            "job_id": job["job_id"],
        },
    )

    await db.commit()

    await enqueue_analysis_job(
        job_id=job["job_id"],
        upload_id=job["upload_id"],
        user_id=job["user_id"],
        file_type=job["file_type"],
        stored_path=job["stored_path"],
        mime_type=job["mime_type"],
    )

    return {
        "message": "Job has been requeued successfully.",
        "job_id": str(job["job_id"]),
        "upload_id": str(job["upload_id"]),
        "status": "queued",
    }
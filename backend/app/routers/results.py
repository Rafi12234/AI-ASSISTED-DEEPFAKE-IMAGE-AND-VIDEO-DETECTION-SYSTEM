import uuid
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.core import User


router = APIRouter(prefix="/results", tags=["Results"])


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


async def get_job_for_user(
    *,
    db: AsyncSession,
    job_id: uuid.UUID,
    user_id: uuid.UUID,
) -> dict[str, Any] | None:
    result = await db.execute(
        text(
            """
            SELECT
                aj.id AS job_id,
                aj.status AS job_status,
                aj.media_upload_id AS upload_id,
                aj.queued_at,
                aj.started_at,
                aj.completed_at,
                aj.error_message,

                mu.original_filename,
                mu.file_type,
                mu.mime_type,
                mu.file_size_bytes,
                mu.upload_status,
                mu.created_at AS uploaded_at
            FROM analysis_jobs aj
            INNER JOIN media_uploads mu ON mu.id = aj.media_upload_id
            WHERE aj.id = :job_id
              AND mu.user_id = :user_id
              AND mu.is_deleted = false
            LIMIT 1
            """
        ),
        {
            "job_id": job_id,
            "user_id": user_id,
        },
    )

    row = result.first()

    if row is None:
        return None

    return row_to_dict(row)


async def get_latest_job_for_upload(
    *,
    db: AsyncSession,
    upload_id: uuid.UUID,
    user_id: uuid.UUID,
) -> dict[str, Any] | None:
    result = await db.execute(
        text(
            """
            SELECT
                aj.id AS job_id,
                aj.status AS job_status,
                aj.media_upload_id AS upload_id,
                aj.queued_at,
                aj.started_at,
                aj.completed_at,
                aj.error_message,

                mu.original_filename,
                mu.file_type,
                mu.mime_type,
                mu.file_size_bytes,
                mu.upload_status,
                mu.created_at AS uploaded_at
            FROM media_uploads mu
            LEFT JOIN analysis_jobs aj ON aj.media_upload_id = mu.id
            WHERE mu.id = :upload_id
              AND mu.user_id = :user_id
              AND mu.is_deleted = false
            ORDER BY aj.queued_at DESC NULLS LAST
            LIMIT 1
            """
        ),
        {
            "upload_id": upload_id,
            "user_id": user_id,
        },
    )

    row = result.first()

    if row is None:
        return None

    return row_to_dict(row)


async def get_analysis_result(
    *,
    db: AsyncSession,
    job_id: uuid.UUID,
) -> dict[str, Any] | None:
    result = await db.execute(
        text(
            """
            SELECT
                id,
                media_upload_id,
                analysis_job_id,
                final_score,
                risk_level,
                confidence,
                explanation,
                signals_summary,
                model_versions,
                processing_time_ms,
                created_at
            FROM analysis_results
            WHERE analysis_job_id = :job_id
            LIMIT 1
            """
        ),
        {
            "job_id": job_id,
        },
    )

    row = result.first()

    if row is None:
        return None

    return row_to_dict(row)


async def get_model_predictions(
    *,
    db: AsyncSession,
    analysis_result_id: uuid.UUID,
) -> list[dict[str, Any]]:
    result = await db.execute(
        text(
            """
            SELECT
                id,
                analysis_result_id,
                model_name,
                model_version,
                raw_score,
                calibrated_score,
                prediction_label,
                target_region,
                inference_time_ms,
                created_at
            FROM model_predictions
            WHERE analysis_result_id = :analysis_result_id
            ORDER BY created_at ASC
            """
        ),
        {
            "analysis_result_id": analysis_result_id,
        },
    )

    return [row_to_dict(row) for row in result.all()]


async def get_forensic_signals(
    *,
    db: AsyncSession,
    analysis_result_id: uuid.UUID,
) -> list[dict[str, Any]]:
    result = await db.execute(
        text(
            """
            SELECT
                id,
                analysis_result_id,
                signal_type,
                signal_value,
                risk_contribution,
                details,
                created_at
            FROM forensic_signals
            WHERE analysis_result_id = :analysis_result_id
            ORDER BY created_at ASC
            """
        ),
        {
            "analysis_result_id": analysis_result_id,
        },
    )

    return [row_to_dict(row) for row in result.all()]


async def build_result_response(
    *,
    db: AsyncSession,
    job: dict[str, Any],
) -> dict[str, Any]:
    job_id = uuid.UUID(job["job_id"])

    analysis_result = await get_analysis_result(
        db=db,
        job_id=job_id,
    )

    if analysis_result is None:
        return {
            "job": job,
            "result": None,
            "model_predictions": [],
            "forensic_signals": [],
            "message": "Analysis result is not available yet.",
        }

    analysis_result_id = uuid.UUID(analysis_result["id"])

    model_predictions = await get_model_predictions(
        db=db,
        analysis_result_id=analysis_result_id,
    )

    forensic_signals = await get_forensic_signals(
        db=db,
        analysis_result_id=analysis_result_id,
    )

    return {
        "job": job,
        "result": analysis_result,
        "model_predictions": model_predictions,
        "forensic_signals": forensic_signals,
    }


@router.get("/jobs/{job_id}")
async def get_result_by_job_id(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job = await get_job_for_user(
        db=db,
        job_id=job_id,
        user_id=current_user.id,
    )

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )

    return await build_result_response(
        db=db,
        job=job,
    )


@router.get("/uploads/{upload_id}")
async def get_result_by_upload_id(
    upload_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job = await get_latest_job_for_upload(
        db=db,
        upload_id=upload_id,
        user_id=current_user.id,
    )

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload not found.",
        )

    if job["job_id"] is None:
        return {
            "job": job,
            "result": None,
            "model_predictions": [],
            "forensic_signals": [],
            "message": "No analysis job exists for this upload yet.",
        }

    return await build_result_response(
        db=db,
        job=job,
    )
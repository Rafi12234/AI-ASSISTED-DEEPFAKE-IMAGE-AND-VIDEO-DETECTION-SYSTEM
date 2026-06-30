from __future__ import annotations

import asyncio
import json
import traceback
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import redis.asyncio as redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.services.ai_service_client import (
    analyze_image_with_ai_service,
    analyze_video_with_ai_service,
)
from app.services.face_evidence import persist_face_evidence_from_ai_result


QUEUE_NAME = "queue:analysis_jobs"
WORKER_SLEEP_SECONDS = 2


engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def safe_json(value: Any, default: Any) -> str:
    if value is None:
        value = default

    return json.dumps(value, ensure_ascii=False)


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default

        return float(value)
    except Exception:
        return default


def safe_int(value: Any) -> int | None:
    try:
        if value is None:
            return None

        return int(value)
    except Exception:
        return None


def get_payload_id(payload: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = payload.get(key)

        if value:
            return str(value)

    raise ValueError(f"Missing required payload key. Expected one of: {keys}")


def get_payload_filename(payload: dict[str, Any]) -> str:
    return str(
        payload.get("original_filename")
        or payload.get("filename")
        or payload.get("file_name")
        or "uploaded-media"
    )


def get_payload_mime_type(payload: dict[str, Any]) -> str:
    return str(payload.get("mime_type") or "application/octet-stream")


def get_payload_file_type(payload: dict[str, Any]) -> str:
    return str(payload.get("file_type") or payload.get("media_type") or "").lower()


def get_payload_stored_path(payload: dict[str, Any]) -> str:
    return str(payload.get("stored_path") or payload.get("object_name") or "")


async def get_redis_client() -> redis.Redis:
    return redis.from_url(
        settings.redis_url,
        decode_responses=True,
    )


async def fetch_job_context(
    db: AsyncSession,
    job_id: str,
) -> dict[str, Any]:
    result = await db.execute(
        text(
            """
            SELECT
                aj.id AS job_id,
                aj.media_upload_id AS upload_id,
                aj.status AS job_status,

                mu.original_filename,
                mu.stored_path,
                mu.file_type,
                mu.mime_type,
                mu.file_size_bytes
            FROM analysis_jobs aj
            INNER JOIN media_uploads mu ON mu.id = aj.media_upload_id
            WHERE aj.id = :job_id
            LIMIT 1
            """
        ),
        {
            "job_id": job_id,
        },
    )

    row = result.first()

    if row is None:
        raise ValueError(f"Analysis job not found: {job_id}")

    return dict(row._mapping)


async def mark_job_processing(
    db: AsyncSession,
    *,
    job_id: str,
    upload_id: str,
) -> None:
    await db.execute(
        text(
            """
            UPDATE analysis_jobs
            SET
                status = 'processing',
                started_at = NOW(),
                error_message = NULL
            WHERE id = :job_id
            """
        ),
        {
            "job_id": job_id,
        },
    )

    await db.execute(
        text(
            """
            UPDATE media_uploads
            SET status = 'processing'
            WHERE id = :upload_id
            """
        ),
        {
            "upload_id": upload_id,
        },
    )


async def mark_job_failed(
    db: AsyncSession,
    *,
    job_id: str,
    upload_id: str,
    error_message: str,
) -> None:
    await db.execute(
        text(
            """
            UPDATE analysis_jobs
            SET
                status = 'failed',
                completed_at = NOW(),
                error_message = :error_message
            WHERE id = :job_id
            """
        ),
        {
            "job_id": job_id,
            "error_message": error_message[:4000],
        },
    )

    await db.execute(
        text(
            """
            UPDATE media_uploads
            SET status = 'failed'
            WHERE id = :upload_id
            """
        ),
        {
            "upload_id": upload_id,
        },
    )


async def mark_job_completed(
    db: AsyncSession,
    *,
    job_id: str,
    upload_id: str,
) -> None:
    await db.execute(
        text(
            """
            UPDATE analysis_jobs
            SET
                status = 'completed',
                completed_at = NOW(),
                error_message = NULL
            WHERE id = :job_id
            """
        ),
        {
            "job_id": job_id,
        },
    )

    await db.execute(
        text(
            """
            UPDATE media_uploads
            SET status = 'analyzed'
            WHERE id = :upload_id
            """
        ),
        {
            "upload_id": upload_id,
        },
    )


async def insert_analysis_result(
    db: AsyncSession,
    *,
    upload_id: str,
    job_id: str,
    analysis_data: dict[str, Any],
) -> str:
    result = await db.execute(
        text(
            """
            INSERT INTO analysis_results (
                media_upload_id,
                analysis_job_id,
                final_score,
                risk_level,
                confidence,
                explanation,
                signals_summary,
                model_versions,
                processing_time_ms
            )
            VALUES (
                :media_upload_id,
                :analysis_job_id,
                :final_score,
                :risk_level,
                :confidence,
                :explanation,
                CAST(:signals_summary AS jsonb),
                CAST(:model_versions AS jsonb),
                :processing_time_ms
            )
            RETURNING id
            """
        ),
        {
            "media_upload_id": upload_id,
            "analysis_job_id": job_id,
            "final_score": safe_float(analysis_data.get("final_score")),
            "risk_level": str(analysis_data.get("risk_level") or "uncertain"),
            "confidence": safe_float(analysis_data.get("confidence")),
            "explanation": str(
                analysis_data.get("explanation") or "Analysis completed."
            ),
            "signals_summary": safe_json(
                analysis_data.get("signals_summary"),
                {},
            ),
            "model_versions": safe_json(
                analysis_data.get("model_versions"),
                {},
            ),
            "processing_time_ms": safe_int(
                analysis_data.get("processing_time_ms")
            ),
        },
    )

    analysis_result_id = result.scalar_one()

    return str(analysis_result_id)


async def insert_model_predictions(
    db: AsyncSession,
    *,
    analysis_result_id: str,
    analysis_data: dict[str, Any],
) -> int:
    predictions = analysis_data.get("model_predictions") or []

    if not isinstance(predictions, list):
        return 0

    saved_count = 0

    for item in predictions:
        if not isinstance(item, dict):
            continue

        await db.execute(
            text(
                """
                INSERT INTO model_predictions (
                    analysis_result_id,
                    model_name,
                    model_version,
                    raw_score,
                    calibrated_score,
                    prediction_label,
                    target_region,
                    inference_time_ms
                )
                VALUES (
                    :analysis_result_id,
                    :model_name,
                    :model_version,
                    :raw_score,
                    :calibrated_score,
                    :prediction_label,
                    :target_region,
                    :inference_time_ms
                )
                """
            ),
            {
                "analysis_result_id": analysis_result_id,
                "model_name": str(item.get("model_name") or "unknown_model"),
                "model_version": str(
                    item.get("model_version") or "unknown_version"
                ),
                "raw_score": safe_float(item.get("raw_score")),
                "calibrated_score": safe_float(
                    item.get("calibrated_score"),
                    safe_float(item.get("raw_score")),
                ),
                "prediction_label": item.get("prediction_label"),
                "target_region": item.get("target_region"),
                "inference_time_ms": safe_int(item.get("inference_time_ms")),
            },
        )

        saved_count += 1

    return saved_count


async def insert_forensic_signals(
    db: AsyncSession,
    *,
    analysis_result_id: str,
    analysis_data: dict[str, Any],
) -> int:
    forensic_items: list[dict[str, Any]] = []

    direct_items = analysis_data.get("forensic_signals") or []

    if isinstance(direct_items, list):
        forensic_items.extend(
            [item for item in direct_items if isinstance(item, dict)]
        )

    signals_summary = analysis_data.get("signals_summary") or {}

    if isinstance(signals_summary, dict):
        summary_items = signals_summary.get("signals") or []

        if isinstance(summary_items, list):
            existing_keys = {
                (
                    str(item.get("signal_type")),
                    str(item.get("signal_name")),
                )
                for item in forensic_items
            }

            for item in summary_items:
                if not isinstance(item, dict):
                    continue

                key = (
                    str(item.get("signal_type")),
                    str(item.get("signal_name")),
                )

                if key not in existing_keys:
                    forensic_items.append(item)

    saved_count = 0

    for item in forensic_items:
        signal_type = str(item.get("signal_type") or "unknown")
        signal_name = str(
            item.get("signal_name")
            or item.get("signal_value")
            or "unknown_signal"
        )

        details = {
            "signal_name": signal_name,
            "severity": item.get("severity"),
            "description": item.get("description"),
            "raw_data": item.get("raw_data") or item.get("details") or {},
        }

        await db.execute(
            text(
                """
                INSERT INTO forensic_signals (
                    analysis_result_id,
                    signal_type,
                    signal_value,
                    risk_contribution,
                    details
                )
                VALUES (
                    :analysis_result_id,
                    :signal_type,
                    :signal_value,
                    :risk_contribution,
                    CAST(:details AS jsonb)
                )
                """
            ),
            {
                "analysis_result_id": analysis_result_id,
                "signal_type": signal_type,
                "signal_value": signal_name,
                "risk_contribution": safe_float(
                    item.get("score")
                    if item.get("score") is not None
                    else item.get("risk_contribution")
                ),
                "details": safe_json(details, {}),
            },
        )

        saved_count += 1

    return saved_count


def build_mock_analysis(
    *,
    file_type: str,
    stored_path: str,
) -> dict[str, Any]:
    return {
        "engine": "mock-fallback-v1",
        "media_type": file_type,
        "final_score": 0.5,
        "risk_level": "uncertain",
        "confidence": 0.5,
        "explanation": (
            "Mock fallback analysis was used because this file type is not "
            "supported by the current AI service."
        ),
        "processing_time_ms": None,
        "model_predictions": [
            {
                "model_name": "mock_fallback_analyzer",
                "model_version": "mock-v1",
                "raw_score": 0.5,
                "calibrated_score": 0.5,
                "prediction_label": "uncertain",
                "target_region": "global",
                "inference_time_ms": None,
            }
        ],
        "forensic_signals": [],
        "signals_summary": {
            "summary": "Mock fallback analysis.",
            "stored_path": stored_path,
            "signals": [],
            "warnings": [
                "Unsupported file type. No real AI analysis was performed."
            ],
        },
        "model_versions": {
            "engine": "mock-fallback-v1",
            "models": [
                {
                    "model_name": "mock_fallback_analyzer",
                    "model_version": "mock-v1",
                }
            ],
        },
    }


async def run_analysis(
    *,
    payload: dict[str, Any],
    job_context: dict[str, Any],
) -> dict[str, Any]:
    file_type = str(
        payload.get("file_type")
        or job_context.get("file_type")
        or ""
    ).lower()

    stored_path = str(
        payload.get("stored_path")
        or job_context.get("stored_path")
        or ""
    )

    filename = str(
        payload.get("original_filename")
        or payload.get("filename")
        or job_context.get("original_filename")
        or "uploaded-media"
    )

    mime_type = str(
        payload.get("mime_type")
        or job_context.get("mime_type")
        or "application/octet-stream"
    )

    if not stored_path:
        raise ValueError("Stored path is missing from job payload/context.")

    if file_type == "image":
        print("Running AI service image analysis...")

        return await analyze_image_with_ai_service(
            stored_path=stored_path,
            filename=filename,
            mime_type=mime_type,
        )

    if file_type == "video":
        print("Running AI service video analysis...")

        return await analyze_video_with_ai_service(
            stored_path=stored_path,
            filename=filename,
            mime_type=mime_type,
        )

    print(f"Unsupported file type '{file_type}'. Using mock fallback.")

    return build_mock_analysis(
        file_type=file_type or "unknown",
        stored_path=stored_path,
    )


async def process_payload(payload: dict[str, Any]) -> None:
    job_id = get_payload_id(payload, "job_id", "analysis_job_id")

    async with AsyncSessionLocal() as db:
        job_context = await fetch_job_context(db, job_id)

        upload_id = str(
            payload.get("upload_id")
            or payload.get("media_upload_id")
            or job_context.get("upload_id")
        )

        print("=" * 80)
        print(f"Processing analysis job: {job_id}")
        print(f"Upload ID: {upload_id}")
        print(f"File: {job_context.get('original_filename')}")
        print(f"Type: {job_context.get('file_type')}")
        print("=" * 80)

        try:
            await mark_job_processing(
                db,
                job_id=job_id,
                upload_id=upload_id,
            )

            await db.commit()

            analysis_data = await run_analysis(
                payload=payload,
                job_context=job_context,
            )

            async with db.begin():
                analysis_result_id = await insert_analysis_result(
                    db,
                    upload_id=upload_id,
                    job_id=job_id,
                    analysis_data=analysis_data,
                )

                saved_prediction_count = await insert_model_predictions(
                    db,
                    analysis_result_id=analysis_result_id,
                    analysis_data=analysis_data,
                )

                saved_signal_count = await insert_forensic_signals(
                    db,
                    analysis_result_id=analysis_result_id,
                    analysis_data=analysis_data,
                )

                saved_face_count = await persist_face_evidence_from_ai_result(
                    db=db,
                    analysis_result_id=analysis_result_id,
                    raw_result=analysis_data,
                )

                await mark_job_completed(
                    db,
                    job_id=job_id,
                    upload_id=upload_id,
                )

            print(f"Analysis result saved: {analysis_result_id}")
            print(f"Saved {saved_prediction_count} model prediction record(s).")
            print(f"Saved {saved_signal_count} forensic signal record(s).")

            if saved_face_count > 0:
                print(f"Saved {saved_face_count} face evidence record(s).")
            else:
                print("No face evidence records found to save.")

            print(f"Job completed successfully: {job_id}")

        except Exception as exc:
            error_message = str(exc)

            print(f"Job failed: {job_id}")
            print(error_message)
            traceback.print_exc()

            await db.rollback()

            await mark_job_failed(
                db,
                job_id=job_id,
                upload_id=upload_id,
                error_message=error_message,
            )

            await db.commit()


async def worker_loop() -> None:
    redis_client = await get_redis_client()

    print("Deepfake analysis worker started.")
    print(f"Queue: {QUEUE_NAME}")

    while True:
        try:
            queue_item = await redis_client.brpop(
                QUEUE_NAME,
                timeout=5,
            )

            if queue_item is None:
                await asyncio.sleep(WORKER_SLEEP_SECONDS)
                continue

            _, raw_payload = queue_item

            try:
                payload = json.loads(raw_payload)
            except json.JSONDecodeError:
                print(f"Invalid queue payload skipped: {raw_payload}")
                continue

            if not isinstance(payload, dict):
                print(f"Non-object queue payload skipped: {payload}")
                continue

            await process_payload(payload)

        except asyncio.CancelledError:
            raise

        except Exception as exc:
            print(f"Worker loop error: {exc}")
            traceback.print_exc()
            await asyncio.sleep(WORKER_SLEEP_SECONDS)


def main() -> None:
    asyncio.run(worker_loop())


if __name__ == "__main__":
    main()
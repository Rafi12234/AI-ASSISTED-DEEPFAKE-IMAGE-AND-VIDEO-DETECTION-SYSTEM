import argparse
import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.core import AnalysisJob
from app.services.ai_service_client import analyze_image_with_ai_service
from app.services.mock_analysis import build_mock_analysis
from app.services.queue import get_analysis_queue_length, pop_analysis_job


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def json_dumps(value: Any) -> str:
    return json.dumps(value, default=str)


def get_payload_filename(payload: dict[str, Any]) -> str:
    stored_path = str(payload.get("stored_path") or "uploaded-file")
    return stored_path.split("/")[-1] or "uploaded-file"


async def run_analysis(payload: dict[str, Any]) -> dict[str, Any]:
    file_type = str(payload.get("file_type") or "").lower()

    if file_type == "image":
        print("Running AI service image analysis...")

        return await analyze_image_with_ai_service(
            stored_path=str(payload["stored_path"]),
            filename=get_payload_filename(payload),
            mime_type=str(payload.get("mime_type") or "image/jpeg"),
        )

    print("Video analysis is not connected yet. Using mock fallback for non-image file.")

    return build_mock_analysis(
        file_type=file_type or "unknown",
        stored_path=str(payload.get("stored_path") or ""),
    )


async def mark_job_processing(
    db: AsyncSession,
    job: AnalysisJob,
) -> AnalysisJob:
    job.status = "processing"
    job.started_at = utc_now()
    job.error_message = None
    job.job_metadata = {
        "worker_status": "processing",
        "worker_started_at": utc_now().isoformat(),
    }

    await db.commit()
    await db.refresh(job)

    return job


async def mark_job_completed(
    db: AsyncSession,
    job: AnalysisJob,
    result_metadata: dict[str, Any],
) -> AnalysisJob:
    job.status = "completed"
    job.completed_at = utc_now()
    job.error_message = None
    job.job_metadata = {
        "worker_status": "completed",
        "worker_completed_at": utc_now().isoformat(),
        "result": result_metadata,
    }

    await db.commit()
    await db.refresh(job)

    return job


async def mark_job_failed(
    db: AsyncSession,
    job_id: uuid.UUID,
    error_message: str,
) -> None:
    result = await db.execute(
        select(AnalysisJob).where(AnalysisJob.id == job_id)
    )
    job = result.scalar_one_or_none()

    if job is None:
        return

    job.status = "failed"
    job.error_message = error_message
    job.job_metadata = {
        "worker_status": "failed",
        "worker_failed_at": utc_now().isoformat(),
        "error": error_message,
    }

    await db.commit()


async def existing_analysis_result_id(
    db: AsyncSession,
    job_id: uuid.UUID,
) -> uuid.UUID | None:
    result = await db.execute(
        text(
            """
            SELECT id
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

    return row.id


async def create_analysis_result(
    db: AsyncSession,
    job: AnalysisJob,
    analysis_result: dict[str, Any],
) -> uuid.UUID:
    signals = analysis_result.get("forensic_signals", [])
    predictions = analysis_result.get("model_predictions", [])

    signals_summary = analysis_result.get(
        "signals_summary",
        {
            "summary": "Analysis completed.",
            "prediction_count": len(predictions),
            "forensic_signal_count": len(signals),
            "signals": signals,
        },
    )

    model_versions = analysis_result.get(
        "model_versions",
        {
            "engine": analysis_result.get("engine", "unknown-engine"),
            "models": [
                {
                    "model_name": prediction.get("model_name", "unknown-model"),
                    "model_version": prediction.get("model_version", "unknown-version"),
                }
                for prediction in predictions
            ],
        },
    )

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
            "media_upload_id": job.media_upload_id,
            "analysis_job_id": job.id,
            "final_score": float(analysis_result["final_score"]),
            "risk_level": str(analysis_result["risk_level"]),
            "confidence": float(analysis_result.get("confidence", analysis_result["final_score"])),
            "explanation": str(analysis_result.get("explanation", "Analysis completed.")),
            "signals_summary": json_dumps(signals_summary),
            "model_versions": json_dumps(model_versions),
            "processing_time_ms": int(analysis_result.get("processing_time_ms") or 0),
        },
    )

    return result.scalar_one()


async def create_model_predictions(
    db: AsyncSession,
    analysis_result_id: uuid.UUID,
    analysis_result: dict[str, Any],
) -> None:
    predictions = analysis_result.get("model_predictions", [])

    for prediction in predictions:
        raw_score = float(
            prediction.get("raw_score", prediction.get("score", 0.0))
        )

        calibrated_score = float(
            prediction.get("calibrated_score", raw_score)
        )

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
                "model_name": str(prediction.get("model_name", "unknown-model")),
                "model_version": str(prediction.get("model_version", "unknown-version")),
                "raw_score": raw_score,
                "calibrated_score": calibrated_score,
                "prediction_label": str(
                    prediction.get(
                        "prediction_label",
                        analysis_result.get("risk_level", "uncertain"),
                    )
                ),
                "target_region": prediction.get("target_region", "global"),
                "inference_time_ms": int(prediction.get("inference_time_ms") or 0),
            },
        )


async def create_forensic_signals(
    db: AsyncSession,
    analysis_result_id: uuid.UUID,
    analysis_result: dict[str, Any],
) -> None:
    signals = analysis_result.get("forensic_signals", [])

    for signal in signals:
        signal_name = str(
            signal.get("signal_name")
            or signal.get("signal_value")
            or signal.get("signal_type")
            or "unknown_signal"
        )

        signal_score = float(
            signal.get("score", signal.get("risk_contribution", 0.0))
        )

        details = {
            "signal_name": signal_name,
            "severity": signal.get("severity", "unknown"),
            "description": signal.get("description", "No description available."),
            "raw_data": signal.get("raw_data", {}),
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
                "signal_type": str(signal.get("signal_type", "unknown")),
                "signal_value": signal_name,
                "risk_contribution": signal_score,
                "details": json_dumps(details),
            },
        )


async def create_analysis_records(
    db: AsyncSession,
    job: AnalysisJob,
    payload: dict[str, Any],
    analysis_result: dict[str, Any],
) -> dict[str, Any]:
    old_result_id = await existing_analysis_result_id(
        db=db,
        job_id=job.id,
    )

    if old_result_id is not None:
        return {
            "analysis_result_id": str(old_result_id),
            "already_exists": True,
        }

    analysis_result_id = await create_analysis_result(
        db=db,
        job=job,
        analysis_result=analysis_result,
    )

    await create_model_predictions(
        db=db,
        analysis_result_id=analysis_result_id,
        analysis_result=analysis_result,
    )

    await create_forensic_signals(
        db=db,
        analysis_result_id=analysis_result_id,
        analysis_result=analysis_result,
    )

    await db.commit()

    return {
        "analysis_result_id": str(analysis_result_id),
        "already_exists": False,
        "engine": analysis_result.get("engine", "unknown-engine"),
        "final_score": analysis_result.get("final_score"),
        "risk_level": analysis_result.get("risk_level"),
        "upload_id": str(payload.get("upload_id")),
    }


async def process_queue_payload(payload: dict[str, Any]) -> None:
    job_id = uuid.UUID(str(payload["job_id"]))

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(AnalysisJob).where(AnalysisJob.id == job_id)
            )
            job = result.scalar_one_or_none()

            if job is None:
                print(f"Job not found in database: {job_id}")
                return

            if job.status == "completed":
                print(f"Job already completed: {job_id}")
                return

            print(f"Processing job: {job_id}")

            job = await mark_job_processing(
                db=db,
                job=job,
            )

            analysis_result = await run_analysis(payload)

            result_metadata = await create_analysis_records(
                db=db,
                job=job,
                payload=payload,
                analysis_result=analysis_result,
            )

            await mark_job_completed(
                db=db,
                job=job,
                result_metadata=result_metadata,
            )

            print(f"Completed job: {job_id}")
            print(f"Engine: {analysis_result.get('engine')}")
            print(f"Final score: {analysis_result.get('final_score')}")
            print(f"Risk level: {analysis_result.get('risk_level')}")

        except Exception as exc:
            await db.rollback()

            error_message = str(exc)

            await mark_job_failed(
                db=db,
                job_id=job_id,
                error_message=error_message,
            )

            print(f"Failed job: {job_id}")
            print(f"Error: {error_message}")


async def run_worker_loop(poll_interval_seconds: int) -> None:
    print("AI Worker Skeleton started.")
    print("Waiting for Redis jobs...")

    while True:
        payload = await pop_analysis_job()

        if payload is None:
            queue_length = await get_analysis_queue_length()
            print(f"No job found. Queue length: {queue_length}. Waiting...")
            await asyncio.sleep(poll_interval_seconds)
            continue

        await process_queue_payload(payload)


async def run_once() -> None:
    print("AI Worker Skeleton running once...")

    payload = await pop_analysis_job()

    if payload is None:
        print("No job found.")
        return

    await process_queue_payload(payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run analysis worker.")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Process one queued job and exit.",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=3,
        help="Polling interval in seconds.",
    )

    args = parser.parse_args()

    if args.once:
        asyncio.run(run_once())
    else:
        asyncio.run(
            run_worker_loop(
                poll_interval_seconds=args.poll_interval,
            )
        )


if __name__ == "__main__":
    main()
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
from app.services.mock_analysis import build_mock_analysis
from app.services.queue import get_analysis_queue_length, pop_analysis_job


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def json_dumps(value: Any) -> str:
    return json.dumps(value, default=str)


async def run_mock_analysis(payload: dict[str, Any]) -> dict[str, Any]:
    print("Running mock analysis...")
    print(f"File type: {payload.get('file_type')}")
    print(f"Stored path: {payload.get('stored_path')}")

    await asyncio.sleep(3)

    return build_mock_analysis(payload)


async def mark_job_processing(db: AsyncSession, job: AnalysisJob) -> None:
    job.status = "processing"
    job.started_at = utc_now()
    job.error_message = None

    existing_metadata = job.job_metadata or {}
    job.job_metadata = {
        **existing_metadata,
        "worker": {
            "status": "processing",
            "started_at": job.started_at.isoformat(),
        },
    }

    await db.commit()
    await db.refresh(job)


async def mark_job_completed(
    db: AsyncSession,
    job: AnalysisJob,
    result_metadata: dict[str, Any],
) -> None:
    job.status = "completed"
    job.completed_at = utc_now()
    job.error_message = None

    existing_metadata = job.job_metadata or {}
    job.job_metadata = {
        **existing_metadata,
        "worker": {
            "status": "completed",
            "completed_at": job.completed_at.isoformat(),
            "result": result_metadata,
        },
    }

    await db.commit()
    await db.refresh(job)


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
        print(f"Could not mark failed. Job not found: {job_id}")
        return

    job.status = "failed"
    job.error_message = error_message[:1000]

    existing_metadata = job.job_metadata or {}
    job.job_metadata = {
        **existing_metadata,
        "worker": {
            "status": "failed",
            "failed_at": utc_now().isoformat(),
            "error": error_message[:1000],
        },
    }

    await db.commit()
    await db.refresh(job)


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
        {"job_id": job_id},
    )

    row = result.first()

    if row is None:
        return None

    return row[0]


async def create_analysis_result(
    db: AsyncSession,
    job: AnalysisJob,
    mock_result: dict[str, Any],
) -> uuid.UUID:
    signals_summary = {
        "summary": (
            f"Mock analysis completed with {len(mock_result['predictions'])} model predictions "
            f"and {len(mock_result['forensic_signals'])} forensic signals."
        ),
        "prediction_count": len(mock_result["predictions"]),
        "forensic_signal_count": len(mock_result["forensic_signals"]),
        "signals": [
            {
                "signal_type": signal["signal_type"],
                "signal_name": signal["signal_name"],
                "score": signal["score"],
                "severity": signal["severity"],
                "description": signal["description"],
            }
            for signal in mock_result["forensic_signals"]
        ],
    }

    model_versions = {
        "engine": "mock-analysis-v1",
        "models": [
            {
                "model_name": prediction["model_name"],
                "model_version": prediction["model_version"],
            }
            for prediction in mock_result["predictions"]
        ],
    }

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
            "final_score": float(mock_result["final_score"]),
            "risk_level": mock_result["risk_level"],
            "confidence": float(mock_result["confidence"]),
            "explanation": mock_result["summary"],
            "signals_summary": json_dumps(signals_summary),
            "model_versions": json_dumps(model_versions),
            "processing_time_ms": 3000,
        },
    )

    return result.scalar_one()


async def create_model_predictions(
    db: AsyncSession,
    analysis_result_id: uuid.UUID,
    mock_result: dict[str, Any],
) -> None:
    for prediction in mock_result["predictions"]:
        raw_score = float(prediction["score"])
        calibrated_score = raw_score

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
                "model_name": prediction["model_name"],
                "model_version": prediction["model_version"],
                "raw_score": raw_score,
                "calibrated_score": calibrated_score,
                "prediction_label": prediction["label"],
                "target_region": "global",
                "inference_time_ms": 1000,
            },
        )


async def create_forensic_signals(
    db: AsyncSession,
    analysis_result_id: uuid.UUID,
    mock_result: dict[str, Any],
) -> None:
    for signal in mock_result["forensic_signals"]:
        details = {
            "signal_name": signal["signal_name"],
            "severity": signal["severity"],
            "description": signal["description"],
            "raw_data": signal["raw_data"],
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
                "signal_type": signal["signal_type"],
                "signal_value": signal["signal_name"],
                "risk_contribution": float(signal["score"]),
                "details": json_dumps(details),
            },
        )


async def create_analysis_records(
    db: AsyncSession,
    job: AnalysisJob,
    payload: dict[str, Any],
    mock_result: dict[str, Any],
) -> dict[str, Any]:
    existing_result = await existing_analysis_result_id(db, job.id)

    if existing_result is not None:
        print(f"Analysis result already exists for job: {job.id}")

        return {
            "analysis_result_id": str(existing_result),
            "final_score": mock_result["final_score"],
            "risk_level": mock_result["risk_level"],
            "message": "Existing analysis result reused.",
        }

    analysis_result_id = await create_analysis_result(
        db=db,
        job=job,
        mock_result=mock_result,
    )

    await create_model_predictions(
        db=db,
        analysis_result_id=analysis_result_id,
        mock_result=mock_result,
    )

    await create_forensic_signals(
        db=db,
        analysis_result_id=analysis_result_id,
        mock_result=mock_result,
    )

    await db.commit()

    return {
        "analysis_result_id": str(analysis_result_id),
        "final_score": mock_result["final_score"],
        "risk_level": mock_result["risk_level"],
        "prediction_count": len(mock_result["predictions"]),
        "forensic_signal_count": len(mock_result["forensic_signals"]),
        "source_file_type": payload.get("file_type"),
    }


async def process_queue_payload(payload: dict[str, Any]) -> None:
    job_id_raw = payload.get("job_id")

    if not job_id_raw:
        print("Skipped queue item because job_id is missing.")
        return

    try:
        job_id = uuid.UUID(str(job_id_raw))
    except ValueError:
        print(f"Skipped queue item because job_id is invalid: {job_id_raw}")
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(AnalysisJob).where(AnalysisJob.id == job_id)
        )
        job = result.scalar_one_or_none()

        if job is None:
            print(f"Skipped queue item. Job not found in database: {job_id}")
            return

        if job.status == "completed":
            print(f"Skipped job because it is already completed: {job_id}")
            return

        try:
            print(f"Processing job: {job_id}")

            await mark_job_processing(db, job)

            mock_result = await run_mock_analysis(payload)

            result_metadata = await create_analysis_records(
                db=db,
                job=job,
                payload=payload,
                mock_result=mock_result,
            )

            await mark_job_completed(db, job, result_metadata)

            print(f"Completed job: {job_id}")
            print(f"Final score: {result_metadata.get('final_score')}")
            print(f"Risk level: {result_metadata.get('risk_level')}")

        except Exception as exc:
            await db.rollback()

            try:
                await mark_job_failed(db, job_id, str(exc))
            except Exception as fail_exc:
                await db.rollback()
                print(f"Could not mark job as failed: {job_id}")
                print(str(fail_exc))

            print(f"Failed job: {job_id}")
            print(str(exc))


async def run_worker_loop(poll_seconds: int = 3) -> None:
    print("AI Worker Skeleton started.")
    print("Waiting for Redis jobs...")

    while True:
        payload = await pop_analysis_job()

        if payload is None:
            queue_length = await get_analysis_queue_length()
            print(f"No job found. Queue length: {queue_length}. Waiting...")
            await asyncio.sleep(poll_seconds)
            continue

        await process_queue_payload(payload)


async def run_once() -> None:
    print("AI Worker Skeleton running once...")

    payload = await pop_analysis_job()

    if payload is None:
        print("No queued job found.")
        return

    await process_queue_payload(payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="Deepfake analysis worker skeleton")

    parser.add_argument(
        "--once",
        action="store_true",
        help="Process one job and exit.",
    )

    parser.add_argument(
        "--poll-seconds",
        type=int,
        default=3,
        help="Seconds to wait between queue checks.",
    )

    args = parser.parse_args()

    if args.once:
        asyncio.run(run_once())
    else:
        asyncio.run(run_worker_loop(poll_seconds=args.poll_seconds))


if __name__ == "__main__":
    main()


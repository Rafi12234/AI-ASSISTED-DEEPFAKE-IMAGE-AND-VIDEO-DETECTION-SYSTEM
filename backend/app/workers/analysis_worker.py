
import argparse
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.core import AnalysisJob
from app.services.queue import get_analysis_queue_length, pop_analysis_job


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def fake_analysis(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Temporary fake analysis.

    Later chunks will replace this with:
    - image AI detector
    - face detector
    - forensic signal detector
    - video frame analyzer
    - scoring engine
    """
    print("Running fake analysis...")
    print(f"File type: {payload.get('file_type')}")
    print(f"Stored path: {payload.get('stored_path')}")

    await asyncio.sleep(3)

    return {
        "worker_version": "skeleton-v1",
        "message": "Fake analysis completed successfully.",
        "processed_at": utc_now().isoformat(),
    }


async def mark_job_processing(
    db: AsyncSession,
    job: AnalysisJob,
) -> None:
    job.status = "processing"
    job.started_at = utc_now()

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
    job: AnalysisJob,
    error_message: str,
) -> None:
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

            result_metadata = await fake_analysis(payload)

            await mark_job_completed(db, job, result_metadata)
            print(f"Completed job: {job_id}")

        except Exception as exc:
            await mark_job_failed(db, job, str(exc))
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

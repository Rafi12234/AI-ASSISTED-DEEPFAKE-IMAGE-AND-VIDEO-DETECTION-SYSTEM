import json
from datetime import datetime, timezone
from uuid import UUID

from app.services.cache import redis_client


ANALYSIS_QUEUE_KEY = "queue:analysis_jobs"


def make_json_safe(value):
    if isinstance(value, UUID):
        return str(value)

    if isinstance(value, datetime):
        return value.isoformat()

    return value


async def enqueue_analysis_job(
    *,
    job_id: UUID,
    upload_id: UUID,
    user_id: UUID,
    file_type: str,
    stored_path: str,
    mime_type: str,
) -> dict:
    payload = {
        "job_id": str(job_id),
        "upload_id": str(upload_id),
        "user_id": str(user_id),
        "file_type": file_type,
        "stored_path": stored_path,
        "mime_type": mime_type,
        "queued_at": datetime.now(timezone.utc).isoformat(),
    }

    await redis_client.rpush(
        ANALYSIS_QUEUE_KEY,
        json.dumps(payload, default=make_json_safe),
    )

    return payload


async def get_analysis_queue_length() -> int:
    return await redis_client.llen(ANALYSIS_QUEUE_KEY)


async def peek_analysis_queue(limit: int = 10) -> list[dict]:
    raw_items = await redis_client.lrange(ANALYSIS_QUEUE_KEY, 0, limit - 1)

    items = []

    for raw_item in raw_items:
        try:
            items.append(json.loads(raw_item))
        except json.JSONDecodeError:
            items.append({"raw": raw_item})

    return items


async def pop_analysis_job() -> dict | None:
    raw_item = await redis_client.lpop(ANALYSIS_QUEUE_KEY)

    if raw_item is None:
        return None

    return json.loads(raw_item)


async def clear_analysis_queue() -> int:
    return await redis_client.delete(ANALYSIS_QUEUE_KEY)
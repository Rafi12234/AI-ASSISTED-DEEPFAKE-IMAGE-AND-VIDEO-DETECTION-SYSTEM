from fastapi import APIRouter

from app.services.queue import (
    ANALYSIS_QUEUE_KEY,
    clear_analysis_queue,
    get_analysis_queue_length,
    peek_analysis_queue,
)


router = APIRouter(prefix="/dev/queue", tags=["Dev Queue"])


@router.get("/analysis")
async def get_analysis_queue():
    queue_length = await get_analysis_queue_length()
    items = await peek_analysis_queue(limit=20)

    return {
        "queue_key": ANALYSIS_QUEUE_KEY,
        "queue_length": queue_length,
        "items": items,
    }


@router.delete("/analysis")
async def clear_queue():
    deleted_count = await clear_analysis_queue()

    return {
        "status": "cleared",
        "deleted_count": deleted_count,
    }
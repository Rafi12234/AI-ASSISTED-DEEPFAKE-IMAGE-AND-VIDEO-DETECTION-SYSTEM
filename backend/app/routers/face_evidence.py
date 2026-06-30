import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.core import User
from app.services.face_evidence import (
    list_face_evidence_for_result,
    sync_face_evidence_from_result_json,
)

router = APIRouter(prefix="/face-evidence", tags=["Face Evidence"])


@router.get("/results/{result_id}")
async def get_result_face_evidence(
    result_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_face_evidence_for_result(
        db=db,
        current_user=current_user,
        result_id=result_id,
    )


@router.post("/results/{result_id}/sync-from-json")
async def sync_result_face_evidence_from_json(
    result_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await sync_face_evidence_from_result_json(
        db=db,
        current_user=current_user,
        result_id=result_id,
    )
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.core import User
from app.services.face_crop_preview import (
    list_face_crop_previews_for_result,
    resolve_face_crop_preview,
)

router = APIRouter(prefix="/face-crops", tags=["Face Crops"])


@router.get("/results/{result_id}")
async def get_result_face_crop_previews(
    result_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_face_crop_previews_for_result(
        db=db,
        current_user=current_user,
        result_id=result_id,
    )


@router.get("/results/{result_id}/{face_id}/preview")
async def preview_result_face_crop(
    result_id: uuid.UUID,
    face_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    crop_path, content_type = await resolve_face_crop_preview(
        db=db,
        current_user=current_user,
        result_id=result_id,
        face_id=face_id,
    )

    return FileResponse(
        path=str(crop_path),
        media_type=content_type,
        filename=crop_path.name,
    )
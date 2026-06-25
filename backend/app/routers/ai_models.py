import uuid
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_current_user, get_db
from app.models.core import User
from app.services.model_registry import (
    list_ai_model_registry,
    upsert_ai_model_registry,
)
from app.services.production_evidence import (
    build_production_evidence_bundle,
    get_result_context,
)

router = APIRouter(prefix="/ai-models", tags=["AI Models"])


def require_admin(current_user: User) -> None:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )


@router.get("/registry")
async def get_ai_model_registry(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_ai_model_registry(db)


@router.post("/sync")
async def sync_ai_model_registry(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    ai_service_url = settings.ai_service_url.rstrip("/")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{ai_service_url}/models")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not connect to AI service: {exc}",
        ) from exc

    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI service model registry failed: {response.text}",
        )

    payload: dict[str, Any] = response.json()

    synced_count = await upsert_ai_model_registry(
        db=db,
        models=payload.get("registered_models") or [],
        active_models=payload.get("active_models") or {},
    )

    return {
        "message": "AI model registry synced successfully.",
        "synced_count": synced_count,
        "active_models": payload.get("active_models") or {},
    }


@router.get("/results/{result_id}/evidence")
async def get_result_production_evidence(
    result_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    context = await get_result_context(
        db=db,
        result_id=result_id,
    )

    if context is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result not found.",
        )

    if current_user.role != "admin" and str(context["user_id"]) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this result evidence.",
        )

    evidence = await build_production_evidence_bundle(
        db=db,
        result_id=result_id,
    )

    return evidence
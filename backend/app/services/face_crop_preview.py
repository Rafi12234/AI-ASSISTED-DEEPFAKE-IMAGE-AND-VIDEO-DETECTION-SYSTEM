from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import User


PROJECT_ROOT = Path(__file__).resolve().parents[2].parent

ALLOWED_CROP_ROOTS = [
    PROJECT_ROOT / "ai-worker" / "artifacts" / "pipeline_face_crops",
    PROJECT_ROOT / "datasets" / "processed" / "face_crops",
]


def row_to_dict(row: Any) -> dict[str, Any]:
    if hasattr(row, "_mapping"):
        return dict(row._mapping)

    return dict(row)


def normalize_path(path_text: str) -> Path:
    return Path(path_text).resolve()


def is_path_allowed(path: Path) -> bool:
    resolved_path = path.resolve()

    for root in ALLOWED_CROP_ROOTS:
        resolved_root = root.resolve()

        try:
            resolved_path.relative_to(resolved_root)
            return True
        except ValueError:
            continue

    return False


def get_content_type(path: Path) -> str:
    suffix = path.suffix.lower()

    if suffix in {".jpg", ".jpeg", ".jfif"}:
        return "image/jpeg"

    if suffix == ".png":
        return "image/png"

    if suffix == ".webp":
        return "image/webp"

    if suffix == ".bmp":
        return "image/bmp"

    return "application/octet-stream"


async def get_result_with_owner(
    *,
    db: AsyncSession,
    result_id: uuid.UUID,
) -> dict[str, Any] | None:
    result = await db.execute(
        text(
            """
            SELECT
                ar.id AS result_id,
                ar.signals_summary,
                ar.created_at,
                aj.id AS job_id,
                mu.id AS upload_id,
                mu.user_id
            FROM analysis_results ar
            INNER JOIN analysis_jobs aj ON aj.id = ar.analysis_job_id
            INNER JOIN media_uploads mu ON mu.id = aj.media_upload_id
            WHERE ar.id = :result_id
            LIMIT 1
            """
        ),
        {
            "result_id": result_id,
        },
    )

    row = result.first()

    if row is None:
        return None

    return row_to_dict(row)


def assert_result_access(
    *,
    current_user: User,
    result_context: dict[str, Any],
) -> None:
    if current_user.role == "admin":
        return

    if str(result_context["user_id"]) == str(current_user.id):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have access to this face crop.",
    )


def extract_face_evidence_items(
    signals_summary: Any,
) -> list[dict[str, Any]]:
    if not isinstance(signals_summary, dict):
        return []

    face_evidence = signals_summary.get("face_evidence") or []

    if not isinstance(face_evidence, list):
        return []

    return [
        item
        for item in face_evidence
        if isinstance(item, dict)
    ]


def find_face_evidence_item(
    *,
    signals_summary: Any,
    face_id: str,
) -> dict[str, Any] | None:
    face_items = extract_face_evidence_items(signals_summary)

    for item in face_items:
        if str(item.get("face_id")) == str(face_id):
            return item

    return None


def get_crop_path_from_face_item(
    face_item: dict[str, Any],
) -> Path:
    crop_path_text = face_item.get("crop_path")

    if not crop_path_text:
        details = face_item.get("details") or {}

        if isinstance(details, dict):
            crop_path_text = details.get("crop_path")

    if not crop_path_text:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Crop path was not found for this face evidence.",
        )

    crop_path = normalize_path(str(crop_path_text))

    if not is_path_allowed(crop_path):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Crop path is outside the allowed preview directories.",
        )

    if not crop_path.exists() or not crop_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Face crop file does not exist anymore.",
        )

    return crop_path


async def resolve_face_crop_preview(
    *,
    db: AsyncSession,
    current_user: User,
    result_id: uuid.UUID,
    face_id: str,
) -> tuple[Path, str]:
    result_context = await get_result_with_owner(
        db=db,
        result_id=result_id,
    )

    if result_context is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result not found.",
        )

    assert_result_access(
        current_user=current_user,
        result_context=result_context,
    )

    face_item = find_face_evidence_item(
        signals_summary=result_context.get("signals_summary"),
        face_id=face_id,
    )

    if face_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Face evidence not found for this result.",
        )

    crop_path = get_crop_path_from_face_item(face_item)

    return crop_path, get_content_type(crop_path)


async def list_face_crop_previews_for_result(
    *,
    db: AsyncSession,
    current_user: User,
    result_id: uuid.UUID,
) -> dict[str, Any]:
    result_context = await get_result_with_owner(
        db=db,
        result_id=result_id,
    )

    if result_context is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result not found.",
        )

    assert_result_access(
        current_user=current_user,
        result_context=result_context,
    )

    face_items = extract_face_evidence_items(
        result_context.get("signals_summary"),
    )

    previews = []

    for item in face_items:
        face_id = str(item.get("face_id") or "")

        if not face_id:
            continue

        previews.append(
            {
                "face_id": face_id,
                "preview_url": f"/api/face-crops/results/{result_id}/{face_id}/preview",
                "face_score": item.get("face_score"),
                "predicted_label": item.get("predicted_label"),
                "quality_score": item.get("quality_score"),
                "bbox": item.get("bbox"),
            }
        )

    return {
        "result_id": str(result_id),
        "face_count": len(previews),
        "previews": previews,
    }
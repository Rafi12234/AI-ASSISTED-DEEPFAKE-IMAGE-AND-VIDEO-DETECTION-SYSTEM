from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import User


def row_to_dict(row: Any) -> dict[str, Any]:
    if hasattr(row, "_mapping"):
        return dict(row._mapping)

    return dict(row)


def safe_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except Exception:
        return None


def safe_int(value: Any) -> int | None:
    if value is None:
        return None

    try:
        return int(value)
    except Exception:
        return None


def ensure_json_text(value: Any, default: Any) -> str:
    if value is None:
        value = default

    return json.dumps(value, ensure_ascii=False)


def extract_face_evidence_items(raw_result: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    top_level_items = raw_result.get("face_evidence") or []

    if isinstance(top_level_items, list):
        items.extend([item for item in top_level_items if isinstance(item, dict)])

    signals_summary = raw_result.get("signals_summary") or {}

    if isinstance(signals_summary, dict):
        summary_items = signals_summary.get("face_evidence") or []

        if isinstance(summary_items, list):
            for item in summary_items:
                if isinstance(item, dict):
                    existing_ids = {str(existing.get("face_id")) for existing in items}
                    item_id = str(item.get("face_id"))

                    if item_id not in existing_ids:
                        items.append(item)

    pipeline = raw_result.get("pipeline") or {}

    if isinstance(pipeline, dict):
        pipeline_items = pipeline.get("face_evidence") or []

        if isinstance(pipeline_items, list):
            for item in pipeline_items:
                if isinstance(item, dict):
                    existing_ids = {str(existing.get("face_id")) for existing in items}
                    item_id = str(item.get("face_id"))

                    if item_id not in existing_ids:
                        items.append(item)

    return items


def get_nested_value(
    *,
    item: dict[str, Any],
    key: str,
) -> Any:
    if key in item and item.get(key) is not None:
        return item.get(key)

    details = item.get("details") or {}

    if isinstance(details, dict) and key in details:
        return details.get(key)

    inner_details = details.get("details") if isinstance(details, dict) else {}

    if isinstance(inner_details, dict) and key in inner_details:
        return inner_details.get(key)

    return None


def normalize_bbox(item: dict[str, Any]) -> Any:
    bbox = get_nested_value(item=item, key="bbox")

    if bbox is None:
        return []

    return bbox


async def persist_face_evidence_from_ai_result(
    *,
    db: AsyncSession,
    analysis_result_id: uuid.UUID | str,
    raw_result: dict[str, Any],
) -> int:
    face_items = extract_face_evidence_items(raw_result)

    if not face_items:
        return 0

    saved_count = 0

    for index, item in enumerate(face_items):
        face_id = str(item.get("face_id") or f"face_{index + 1}")

        bbox = normalize_bbox(item)

        detection_confidence = safe_float(
            get_nested_value(item=item, key="detection_confidence")
            or get_nested_value(item=item, key="confidence")
        )

        face_score = safe_float(
            get_nested_value(item=item, key="face_score")
            or get_nested_value(item=item, key="fake_probability")
        )

        frame_number = safe_int(get_nested_value(item=item, key="frame_number"))
        timestamp_seconds = safe_float(get_nested_value(item=item, key="timestamp_seconds"))

        crop_path = get_nested_value(item=item, key="crop_path")
        heatmap_path = get_nested_value(item=item, key="heatmap_path")

        quality_score = safe_float(get_nested_value(item=item, key="quality_score"))

        model_name = get_nested_value(item=item, key="model_name")
        model_version = get_nested_value(item=item, key="model_version")
        predicted_label = get_nested_value(item=item, key="predicted_label")

        await db.execute(
            text(
                """
                INSERT INTO face_evidence (
                    analysis_result_id,
                    face_id,
                    bbox,
                    detection_confidence,
                    face_score,
                    frame_number,
                    timestamp_seconds,
                    crop_path,
                    heatmap_path,
                    quality_score,
                    model_name,
                    model_version,
                    predicted_label,
                    details
                )
                VALUES (
                    :analysis_result_id,
                    :face_id,
                    CAST(:bbox AS jsonb),
                    :detection_confidence,
                    :face_score,
                    :frame_number,
                    :timestamp_seconds,
                    :crop_path,
                    :heatmap_path,
                    :quality_score,
                    :model_name,
                    :model_version,
                    :predicted_label,
                    CAST(:details AS jsonb)
                )
                ON CONFLICT (analysis_result_id, face_id)
                DO UPDATE SET
                    bbox = EXCLUDED.bbox,
                    detection_confidence = EXCLUDED.detection_confidence,
                    face_score = EXCLUDED.face_score,
                    frame_number = EXCLUDED.frame_number,
                    timestamp_seconds = EXCLUDED.timestamp_seconds,
                    crop_path = EXCLUDED.crop_path,
                    heatmap_path = EXCLUDED.heatmap_path,
                    quality_score = EXCLUDED.quality_score,
                    model_name = EXCLUDED.model_name,
                    model_version = EXCLUDED.model_version,
                    predicted_label = EXCLUDED.predicted_label,
                    details = EXCLUDED.details
                """
            ),
            {
                "analysis_result_id": analysis_result_id,
                "face_id": face_id,
                "bbox": ensure_json_text(bbox, []),
                "detection_confidence": detection_confidence,
                "face_score": face_score,
                "frame_number": frame_number,
                "timestamp_seconds": timestamp_seconds,
                "crop_path": str(crop_path) if crop_path else None,
                "heatmap_path": str(heatmap_path) if heatmap_path else None,
                "quality_score": quality_score,
                "model_name": str(model_name) if model_name else None,
                "model_version": str(model_version) if model_version else None,
                "predicted_label": str(predicted_label) if predicted_label else None,
                "details": ensure_json_text(item, {}),
            },
        )

        saved_count += 1

    return saved_count


async def get_result_context(
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
        detail="You do not have access to this face evidence.",
    )


async def list_face_evidence_for_result(
    *,
    db: AsyncSession,
    current_user: User,
    result_id: uuid.UUID,
) -> dict[str, Any]:
    result_context = await get_result_context(
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

    result = await db.execute(
        text(
            """
            SELECT
                id,
                analysis_result_id,
                face_id,
                bbox,
                detection_confidence,
                face_score,
                frame_number,
                timestamp_seconds,
                crop_path,
                heatmap_path,
                quality_score,
                model_name,
                model_version,
                predicted_label,
                details,
                created_at
            FROM face_evidence
            WHERE analysis_result_id = :result_id
            ORDER BY
                COALESCE(face_score, 0) DESC,
                created_at ASC
            """
        ),
        {
            "result_id": result_id,
        },
    )

    rows = [row_to_dict(row) for row in result.all()]

    return {
        "result_id": str(result_id),
        "face_count": len(rows),
        "faces": rows,
    }


async def sync_face_evidence_from_result_json(
    *,
    db: AsyncSession,
    current_user: User,
    result_id: uuid.UUID,
) -> dict[str, Any]:
    result_context = await get_result_context(
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

    raw_result = {
        "signals_summary": result_context.get("signals_summary") or {},
    }

    saved_count = await persist_face_evidence_from_ai_result(
        db=db,
        analysis_result_id=result_id,
        raw_result=raw_result,
    )

    await db.commit()

    return {
        "result_id": str(result_id),
        "saved_count": saved_count,
    }
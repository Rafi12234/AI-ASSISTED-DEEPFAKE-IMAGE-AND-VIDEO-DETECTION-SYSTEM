from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.model_registry import (
    list_model_evidence_for_result,
    row_to_dict,
)


def safe_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value

    return {}


def normalize_prediction_as_model_evidence(row: dict[str, Any]) -> dict[str, Any]:
    score = row.get("calibrated_score")

    if score is None:
        score = row.get("raw_score")

    return {
        "id": None,
        "analysis_result_id": row.get("analysis_result_id"),
        "model_name": row.get("model_name") or "unknown_model",
        "model_version": row.get("model_version") or "unknown_version",
        "model_type": "legacy_model_prediction",
        "input_type": row.get("target_region") or "global",
        "score": float(score or 0.0),
        "confidence": None,
        "latency_ms": row.get("inference_time_ms"),
        "device": "cpu",
        "details": {
            "source": "model_predictions_fallback",
            "raw_score": row.get("raw_score"),
            "calibrated_score": row.get("calibrated_score"),
            "prediction_label": row.get("prediction_label"),
            "target_region": row.get("target_region"),
        },
        "created_at": row.get("created_at"),
    }


def normalize_forensic_signal(row: dict[str, Any]) -> dict[str, Any]:
    details = safe_dict(row.get("details"))

    return {
        "id": row.get("id"),
        "analysis_result_id": row.get("analysis_result_id"),
        "signal_type": row.get("signal_type"),
        "signal_name": details.get("signal_name") or row.get("signal_value"),
        "score": row.get("risk_contribution"),
        "severity": details.get("severity"),
        "description": details.get("description"),
        "raw_data": details.get("raw_data") or details,
        "created_at": row.get("created_at"),
    }


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
                ar.final_score,
                ar.risk_level,
                ar.confidence,
                ar.explanation,
                ar.signals_summary,
                ar.model_versions,
                ar.processing_time_ms,
                ar.created_at AS result_created_at,

                aj.id AS job_id,
                aj.status AS job_status,

                mu.id AS upload_id,
                mu.user_id,
                mu.original_filename,
                mu.file_type,
                mu.mime_type
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


async def get_legacy_model_prediction_evidence(
    *,
    db: AsyncSession,
    result_id: uuid.UUID,
) -> list[dict[str, Any]]:
    result = await db.execute(
        text(
            """
            SELECT
                id,
                analysis_result_id,
                model_name,
                model_version,
                raw_score,
                calibrated_score,
                prediction_label,
                target_region,
                inference_time_ms,
                created_at
            FROM model_predictions
            WHERE analysis_result_id = :result_id
            ORDER BY created_at ASC
            """
        ),
        {
            "result_id": result_id,
        },
    )

    rows = [row_to_dict(row) for row in result.all()]

    return [normalize_prediction_as_model_evidence(row) for row in rows]


async def get_forensic_evidence(
    *,
    db: AsyncSession,
    result_id: uuid.UUID,
) -> list[dict[str, Any]]:
    result = await db.execute(
        text(
            """
            SELECT
                id,
                analysis_result_id,
                signal_type,
                signal_value,
                risk_contribution,
                details,
                created_at
            FROM forensic_signals
            WHERE analysis_result_id = :result_id
            ORDER BY created_at ASC
            """
        ),
        {
            "result_id": result_id,
        },
    )

    rows = [row_to_dict(row) for row in result.all()]

    return [normalize_forensic_signal(row) for row in rows]


async def build_production_evidence_bundle(
    *,
    db: AsyncSession,
    result_id: uuid.UUID,
) -> dict[str, Any] | None:
    context = await get_result_context(
        db=db,
        result_id=result_id,
    )

    if context is None:
        return None

    signals_summary = safe_dict(context.get("signals_summary"))
    model_versions = safe_dict(context.get("model_versions"))

    model_evidence = await list_model_evidence_for_result(
        db=db,
        result_id=result_id,
    )

    if not model_evidence:
        model_evidence = await get_legacy_model_prediction_evidence(
            db=db,
            result_id=result_id,
        )

    forensic_evidence = await get_forensic_evidence(
        db=db,
        result_id=result_id,
    )

    production_pipeline = signals_summary.get("production_pipeline") or {}
    interpretation = signals_summary.get("interpretation") or {}

    frame_evidence = (
        signals_summary.get("frame_evidence")
        or signals_summary.get("sampled_frames")
        or []
    )

    return {
        "result_id": str(result_id),
        "job_id": context.get("job_id"),
        "upload_id": context.get("upload_id"),
        "media": {
            "filename": context.get("original_filename"),
            "file_type": context.get("file_type"),
            "mime_type": context.get("mime_type"),
        },
        "summary": {
            "final_score": context.get("final_score"),
            "risk_level": context.get("risk_level"),
            "confidence": context.get("confidence"),
            "processing_time_ms": context.get("processing_time_ms"),
            "engine": model_versions.get("engine"),
            "pipeline_version": production_pipeline.get("pipeline_version"),
        },
        "interpretation": interpretation,
        "model_versions": model_versions,
        "production_pipeline": production_pipeline,
        "model_evidence": model_evidence,
        "forensic_evidence": forensic_evidence,
        "face_evidence": signals_summary.get("face_evidence") or [],
        "frame_evidence": frame_evidence,
        "audio_evidence": signals_summary.get("audio_evidence"),
        "raw_signals_summary": signals_summary,
    }
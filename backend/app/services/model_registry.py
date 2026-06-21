from __future__ import annotations

import json
import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def make_json_safe(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, uuid.UUID):
        return str(value)

    if isinstance(value, dict):
        return {key: make_json_safe(item) for key, item in value.items()}

    if isinstance(value, list):
        return [make_json_safe(item) for item in value]

    return value


def row_to_dict(row: Any) -> dict[str, Any]:
    return {
        key: make_json_safe(value)
        for key, value in row._mapping.items()
    }


def json_dumps(value: Any) -> str:
    return json.dumps(make_json_safe(value or {}))


async def upsert_ai_model_registry(
    *,
    db: AsyncSession,
    models: list[dict[str, Any]],
    active_models: dict[str, str] | None = None,
) -> int:
    active_model_names = set((active_models or {}).values())

    synced_count = 0

    for model in models:
        model_name = str(model.get("model_name") or "").strip()
        model_version = str(model.get("model_version") or "").strip()

        if not model_name or not model_version:
            continue

        is_active = model_name in active_model_names

        await db.execute(
            text(
                """
                INSERT INTO ai_model_registry (
                    model_name,
                    model_version,
                    model_type,
                    input_type,
                    checkpoint_path,
                    runtime_provider,
                    device,
                    dataset_used,
                    is_trainable,
                    is_enabled,
                    is_active,
                    description,
                    training_metrics,
                    evaluation_metrics,
                    extra_metadata,
                    updated_at
                )
                VALUES (
                    :model_name,
                    :model_version,
                    :model_type,
                    :input_type,
                    :checkpoint_path,
                    :runtime_provider,
                    :device,
                    :dataset_used,
                    :is_trainable,
                    :is_enabled,
                    :is_active,
                    :description,
                    CAST(:training_metrics AS JSONB),
                    CAST(:evaluation_metrics AS JSONB),
                    CAST(:extra_metadata AS JSONB),
                    NOW()
                )
                ON CONFLICT (model_name, model_version)
                DO UPDATE SET
                    model_type = EXCLUDED.model_type,
                    input_type = EXCLUDED.input_type,
                    checkpoint_path = EXCLUDED.checkpoint_path,
                    runtime_provider = EXCLUDED.runtime_provider,
                    device = EXCLUDED.device,
                    dataset_used = EXCLUDED.dataset_used,
                    is_trainable = EXCLUDED.is_trainable,
                    is_enabled = EXCLUDED.is_enabled,
                    is_active = EXCLUDED.is_active,
                    description = EXCLUDED.description,
                    training_metrics = EXCLUDED.training_metrics,
                    evaluation_metrics = EXCLUDED.evaluation_metrics,
                    extra_metadata = EXCLUDED.extra_metadata,
                    updated_at = NOW()
                """
            ),
            {
                "model_name": model_name,
                "model_version": model_version,
                "model_type": model.get("model_type") or "unknown",
                "input_type": model.get("input_type") or "unknown",
                "checkpoint_path": model.get("checkpoint_path"),
                "runtime_provider": model.get("runtime_provider") or "unknown",
                "device": model.get("device") or "cpu",
                "dataset_used": model.get("dataset_used"),
                "is_trainable": bool(model.get("is_trainable", False)),
                "is_enabled": bool(model.get("is_enabled", True)),
                "is_active": is_active,
                "description": model.get("description"),
                "training_metrics": json_dumps(model.get("training_metrics")),
                "evaluation_metrics": json_dumps(model.get("evaluation_metrics")),
                "extra_metadata": json_dumps(
                    {
                        "source": "ai_service_sync",
                        "raw_model": model,
                    }
                ),
            },
        )

        synced_count += 1

    await db.commit()

    return synced_count


async def list_ai_model_registry(db: AsyncSession) -> list[dict[str, Any]]:
    result = await db.execute(
        text(
            """
            SELECT
                id,
                model_name,
                model_version,
                model_type,
                input_type,
                checkpoint_path,
                runtime_provider,
                device,
                dataset_used,
                is_trainable,
                is_enabled,
                is_active,
                description,
                training_metrics,
                evaluation_metrics,
                extra_metadata,
                created_at,
                updated_at
            FROM ai_model_registry
            ORDER BY is_active DESC, model_type ASC, model_name ASC
            """
        )
    )

    return [row_to_dict(row) for row in result.all()]


async def store_analysis_model_evidence(
    *,
    db: AsyncSession,
    analysis_result_id: uuid.UUID,
    analysis_data: dict[str, Any],
) -> int:
    pipeline = analysis_data.get("pipeline") or {}
    evidence_items = pipeline.get("model_evidence") or []

    if not evidence_items:
        return 0

    inserted_count = 0

    for item in evidence_items:
        await db.execute(
            text(
                """
                INSERT INTO analysis_model_evidence (
                    analysis_result_id,
                    model_name,
                    model_version,
                    model_type,
                    input_type,
                    score,
                    confidence,
                    latency_ms,
                    device,
                    details
                )
                VALUES (
                    :analysis_result_id,
                    :model_name,
                    :model_version,
                    :model_type,
                    :input_type,
                    :score,
                    :confidence,
                    :latency_ms,
                    :device,
                    CAST(:details AS JSONB)
                )
                """
            ),
            {
                "analysis_result_id": analysis_result_id,
                "model_name": item.get("model_name") or "unknown_model",
                "model_version": item.get("model_version") or "unknown_version",
                "model_type": item.get("model_type") or "unknown",
                "input_type": item.get("input_type") or "unknown",
                "score": float(item.get("score") or 0.0),
                "confidence": float(item.get("confidence") or 0.0),
                "latency_ms": item.get("latency_ms"),
                "device": item.get("device") or "cpu",
                "details": json_dumps(item.get("details")),
            },
        )

        inserted_count += 1

    return inserted_count


async def list_model_evidence_for_result(
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
                model_type,
                input_type,
                score,
                confidence,
                latency_ms,
                device,
                details,
                created_at
            FROM analysis_model_evidence
            WHERE analysis_result_id = :result_id
            ORDER BY created_at ASC
            """
        ),
        {
            "result_id": result_id,
        },
    )

    return [row_to_dict(row) for row in result.all()]
from __future__ import annotations

import time
from typing import Any

from app.schemas.analysis import (
    AnalysisPipelineResult,
    FaceEvidence,
    ForensicEvidence,
    FrameEvidence,
    ModelEvidence,
)


def get_risk_level(final_score: float) -> str:
    if final_score < 0.33:
        return "likely_authentic"

    if final_score < 0.61:
        return "uncertain"

    if final_score < 0.80:
        return "suspicious"

    return "high_risk"


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default

        return float(value)

    except Exception:
        return default


def normalize_model_evidence(
    raw_result: dict[str, Any],
) -> list[ModelEvidence]:
    model_items = []

    for item in raw_result.get("model_predictions", []):
        model_items.append(
            ModelEvidence(
                model_name=str(item.get("model_name") or "unknown_model"),
                model_version=str(item.get("model_version") or "unknown_version"),
                model_type=str(item.get("model_type") or "foundation_detector"),
                input_type=str(item.get("target_region") or "global"),
                score=safe_float(
                    item.get("calibrated_score")
                    if item.get("calibrated_score") is not None
                    else item.get("raw_score")
                ),
                confidence=safe_float(raw_result.get("confidence"), 0.0),
                latency_ms=item.get("inference_time_ms"),
                device=str(item.get("device") or "cpu"),
                details={
                    "prediction_label": item.get("prediction_label"),
                    "raw_score": item.get("raw_score"),
                    "calibrated_score": item.get("calibrated_score"),
                },
            )
        )

    return model_items


def normalize_forensic_evidence(
    raw_result: dict[str, Any],
) -> list[ForensicEvidence]:
    forensic_items = []

    signals_summary = raw_result.get("signals_summary") or {}
    signals = signals_summary.get("signals") or raw_result.get("forensic_signals") or []

    for signal in signals:
        forensic_items.append(
            ForensicEvidence(
                signal_type=str(signal.get("signal_type") or "unknown"),
                signal_name=str(
                    signal.get("signal_name")
                    or signal.get("signal_value")
                    or "unknown_signal"
                ),
                score=safe_float(
                    signal.get("score")
                    if signal.get("score") is not None
                    else signal.get("risk_contribution")
                ),
                severity=str(signal.get("severity") or "unknown"),
                description=str(
                    signal.get("description") or "No description available."
                ),
                raw_data=signal.get("raw_data") or signal.get("details") or {},
            )
        )

    return forensic_items


def normalize_bbox(value: Any) -> list[float]:
    if isinstance(value, list):
        return [safe_float(item) for item in value]

    if isinstance(value, dict):
        x = safe_float(value.get("x"))
        y = safe_float(value.get("y"))
        width = safe_float(value.get("width"))
        height = safe_float(value.get("height"))

        return [x, y, width, height]

    return []


def normalize_face_evidence(
    raw_result: dict[str, Any],
) -> list[FaceEvidence]:
    signals_summary = raw_result.get("signals_summary") or {}
    raw_face_items = signals_summary.get("face_evidence") or raw_result.get("face_evidence") or []

    face_items: list[FaceEvidence] = []

    for index, item in enumerate(raw_face_items):
        if not isinstance(item, dict):
            continue

        details = item.get("details") or {}
        bbox = item.get("bbox") or details.get("bbox") or {}

        face_items.append(
            FaceEvidence(
                face_id=str(item.get("face_id") or f"face_{index + 1}"),
                bbox=normalize_bbox(bbox),
                detection_confidence=(
                    safe_float(item.get("detection_confidence"))
                    if item.get("detection_confidence") is not None
                    else safe_float(details.get("confidence"))
                    if details.get("confidence") is not None
                    else None
                ),
                face_score=(
                    safe_float(item.get("face_score"))
                    if item.get("face_score") is not None
                    else safe_float(item.get("fake_probability"))
                    if item.get("fake_probability") is not None
                    else None
                ),
                frame_number=item.get("frame_number"),
                timestamp_seconds=item.get("timestamp_seconds"),
                crop_path=item.get("crop_path") or details.get("crop_path"),
                heatmap_path=item.get("heatmap_path"),
                details={
                    **item,
                    "source": "signals_summary.face_evidence",
                },
            )
        )

    return face_items


def normalize_frame_evidence(
    raw_result: dict[str, Any],
) -> list[FrameEvidence]:
    signals_summary = raw_result.get("signals_summary") or {}

    raw_frame_items = (
        signals_summary.get("frame_evidence")
        or signals_summary.get("sampled_frames")
        or raw_result.get("frame_evidence")
        or []
    )

    frame_items: list[FrameEvidence] = []

    for item in raw_frame_items:
        if not isinstance(item, dict):
            continue

        frame_score = safe_float(
            item.get("frame_score")
            if item.get("frame_score") is not None
            else item.get("final_score")
        )

        frame_items.append(
            FrameEvidence(
                frame_number=int(item.get("frame_number") or 0),
                timestamp_seconds=item.get("timestamp_seconds"),
                frame_score=frame_score,
                risk_level=str(
                    item.get("risk_level") or get_risk_level(frame_score)
                ),  # type: ignore[arg-type]
                confidence=safe_float(item.get("confidence"), 0.0),
                faces=[],
                details=item,
            )
        )

    return frame_items


def build_pipeline_result(
    *,
    media_type: str,
    raw_result: dict[str, Any],
    started_at: float,
) -> AnalysisPipelineResult:
    final_score = safe_float(raw_result.get("final_score"))
    confidence = safe_float(raw_result.get("confidence"))
    risk_level = str(raw_result.get("risk_level") or get_risk_level(final_score))

    engine = str(
        raw_result.get("engine")
        or raw_result.get("model_versions", {}).get("engine")
        or "unknown-engine"
    )

    model_evidence = normalize_model_evidence(raw_result)
    forensic_evidence = normalize_forensic_evidence(raw_result)
    face_evidence = normalize_face_evidence(raw_result)
    frame_evidence = normalize_frame_evidence(raw_result)

    elapsed_ms = int((time.perf_counter() - started_at) * 1000)

    model_versions = raw_result.get("model_versions") or {
        "engine": engine,
        "models": [
            {
                "model_name": item.model_name,
                "model_version": item.model_version,
            }
            for item in model_evidence
        ],
    }

    signals_summary = raw_result.get("signals_summary") or {}

    production_pipeline = signals_summary.get("production_pipeline") or {}

    production_pipeline.update(
        {
            "pipeline_version": "pipeline-v0.44.0",
            "media_type": media_type,
            "model_evidence_count": len(model_evidence),
            "forensic_evidence_count": len(forensic_evidence),
            "face_evidence_count": len(face_evidence),
            "frame_evidence_count": len(frame_evidence),
            "note": (
                "Production evidence schema now includes model, forensic, "
                "face, and frame evidence."
            ),
        }
    )

    signals_summary["production_pipeline"] = production_pipeline

    if face_evidence and "face_evidence" not in signals_summary:
        signals_summary["face_evidence"] = [
            item.model_dump()
            for item in face_evidence
        ]

    if frame_evidence and "frame_evidence" not in signals_summary:
        signals_summary["frame_evidence"] = [
            item.model_dump()
            for item in frame_evidence
        ]

    return AnalysisPipelineResult(
        media_type=media_type,  # type: ignore[arg-type]
        engine=engine,
        final_score=final_score,
        risk_level=risk_level,  # type: ignore[arg-type]
        confidence=confidence,
        explanation=str(raw_result.get("explanation") or "Analysis completed."),
        model_evidence=model_evidence,
        forensic_evidence=forensic_evidence,
        face_evidence=face_evidence,
        frame_evidence=frame_evidence,
        signals_summary=signals_summary,
        model_versions=model_versions,
        processing_time_ms=raw_result.get("processing_time_ms") or elapsed_ms,
        raw_result=raw_result,
    )


def to_legacy_api_response(
    pipeline_result: AnalysisPipelineResult,
) -> dict[str, Any]:
    raw_result = dict(pipeline_result.raw_result)

    raw_result["engine"] = pipeline_result.engine
    raw_result["final_score"] = pipeline_result.final_score
    raw_result["risk_level"] = pipeline_result.risk_level
    raw_result["confidence"] = pipeline_result.confidence
    raw_result["explanation"] = pipeline_result.explanation
    raw_result["signals_summary"] = pipeline_result.signals_summary
    raw_result["model_versions"] = pipeline_result.model_versions
    raw_result["processing_time_ms"] = pipeline_result.processing_time_ms

    raw_result["face_evidence"] = [
        item.model_dump()
        for item in pipeline_result.face_evidence
    ]

    raw_result["frame_evidence"] = [
        item.model_dump()
        for item in pipeline_result.frame_evidence
    ]

    raw_result["pipeline"] = {
        "version": "pipeline-v0.44.0",
        "media_type": pipeline_result.media_type,
        "engine": pipeline_result.engine,
        "model_evidence": [
            item.model_dump()
            for item in pipeline_result.model_evidence
        ],
        "forensic_evidence": [
            item.model_dump()
            for item in pipeline_result.forensic_evidence
        ],
        "face_evidence": [
            item.model_dump()
            for item in pipeline_result.face_evidence
        ],
        "frame_evidence": [
            item.model_dump()
            for item in pipeline_result.frame_evidence
        ],
        "audio_evidence": (
            pipeline_result.audio_evidence.model_dump()
            if pipeline_result.audio_evidence
            else None
        ),
    }

    return raw_result
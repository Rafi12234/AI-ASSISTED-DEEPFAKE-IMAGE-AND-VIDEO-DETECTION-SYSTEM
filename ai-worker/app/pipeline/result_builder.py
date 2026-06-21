from __future__ import annotations

import time
from typing import Any

from app.schemas.analysis import (
    AnalysisPipelineResult,
    ForensicEvidence,
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


def normalize_model_evidence(raw_result: dict[str, Any]) -> list[ModelEvidence]:
    model_items = []

    for item in raw_result.get("model_predictions", []):
        model_items.append(
            ModelEvidence(
                model_name=str(item.get("model_name") or "unknown_model"),
                model_version=str(item.get("model_version") or "unknown_version"),
                model_type="foundation_detector",
                input_type=str(item.get("target_region") or "global"),
                score=float(item.get("calibrated_score") or item.get("raw_score") or 0.0),
                confidence=float(raw_result.get("confidence") or 0.0),
                latency_ms=item.get("inference_time_ms"),
                device="cpu",
                details={
                    "prediction_label": item.get("prediction_label"),
                    "raw_score": item.get("raw_score"),
                    "calibrated_score": item.get("calibrated_score"),
                },
            )
        )

    return model_items


def normalize_forensic_evidence(raw_result: dict[str, Any]) -> list[ForensicEvidence]:
    forensic_items = []

    signals_summary = raw_result.get("signals_summary") or {}
    signals = signals_summary.get("signals") or raw_result.get("forensic_signals") or []

    for signal in signals:
        forensic_items.append(
            ForensicEvidence(
                signal_type=str(signal.get("signal_type") or "unknown"),
                signal_name=str(signal.get("signal_name") or signal.get("signal_value") or "unknown_signal"),
                score=float(signal.get("score") or signal.get("risk_contribution") or 0.0),
                severity=str(signal.get("severity") or "unknown"),
                description=str(signal.get("description") or "No description available."),
                raw_data=signal.get("raw_data") or signal.get("details") or {},
            )
        )

    return forensic_items


def build_pipeline_result(
    *,
    media_type: str,
    raw_result: dict[str, Any],
    started_at: float,
) -> AnalysisPipelineResult:
    final_score = float(raw_result.get("final_score") or 0.0)
    confidence = float(raw_result.get("confidence") or 0.0)
    risk_level = str(raw_result.get("risk_level") or get_risk_level(final_score))
    engine = str(raw_result.get("engine") or raw_result.get("model_versions", {}).get("engine") or "unknown-engine")

    model_evidence = normalize_model_evidence(raw_result)
    forensic_evidence = normalize_forensic_evidence(raw_result)

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
    signals_summary["production_pipeline"] = {
        "pipeline_version": "pipeline-v0.31.0",
        "media_type": media_type,
        "model_evidence_count": len(model_evidence),
        "forensic_evidence_count": len(forensic_evidence),
        "note": "This is the production pipeline structure. Real DL detectors will be plugged into this architecture in upcoming chunks.",
    }

    return AnalysisPipelineResult(
        media_type=media_type,  # type: ignore[arg-type]
        engine=engine,
        final_score=final_score,
        risk_level=risk_level,  # type: ignore[arg-type]
        confidence=confidence,
        explanation=str(raw_result.get("explanation") or "Analysis completed."),
        model_evidence=model_evidence,
        forensic_evidence=forensic_evidence,
        signals_summary=signals_summary,
        model_versions=model_versions,
        processing_time_ms=raw_result.get("processing_time_ms") or elapsed_ms,
        raw_result=raw_result,
    )


def to_legacy_api_response(pipeline_result: AnalysisPipelineResult) -> dict[str, Any]:
    """
    Keeps compatibility with backend worker.
    Backend currently expects:
    final_score, risk_level, confidence, explanation,
    model_predictions, forensic_signals, signals_summary, model_versions.
    """

    raw_result = dict(pipeline_result.raw_result)

    raw_result["engine"] = pipeline_result.engine
    raw_result["final_score"] = pipeline_result.final_score
    raw_result["risk_level"] = pipeline_result.risk_level
    raw_result["confidence"] = pipeline_result.confidence
    raw_result["explanation"] = pipeline_result.explanation
    raw_result["signals_summary"] = pipeline_result.signals_summary
    raw_result["model_versions"] = pipeline_result.model_versions
    raw_result["processing_time_ms"] = pipeline_result.processing_time_ms

    raw_result["pipeline"] = {
        "version": "pipeline-v0.31.0",
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
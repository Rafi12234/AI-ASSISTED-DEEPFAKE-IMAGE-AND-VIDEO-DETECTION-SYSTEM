import hashlib
from typing import Any


def _stable_score(seed_text: str) -> float:
    """
    Creates a deterministic fake score from job/upload data.
    Same input gives same score.
    Output range: 0.05 to 0.95
    """
    digest = hashlib.sha256(seed_text.encode("utf-8")).hexdigest()
    number = int(digest[:8], 16)
    normalized = number / 0xFFFFFFFF

    return round(0.05 + (normalized * 0.90), 4)


def get_risk_level(score: float) -> str:
    if score < 0.25:
        return "likely_authentic"

    if score < 0.55:
        return "uncertain"

    if score < 0.80:
        return "suspicious"

    return "high_risk"


def get_summary(score: float, risk_level: str) -> str:
    if risk_level == "likely_authentic":
        return (
            "The mock analysis found low manipulation risk. "
            "No strong synthetic-media signals were detected."
        )

    if risk_level == "uncertain":
        return (
            "The mock analysis found mixed signals. "
            "The media should be reviewed with caution."
        )

    if risk_level == "suspicious":
        return (
            "The mock analysis found several suspicious signals. "
            "Human review is recommended."
        )

    return (
        "The mock analysis found high-risk manipulation indicators. "
        "Human review should be prioritized."
    )


def build_mock_analysis(payload: dict[str, Any]) -> dict[str, Any]:
    job_id = str(payload.get("job_id", ""))
    upload_id = str(payload.get("upload_id", ""))
    stored_path = str(payload.get("stored_path", ""))
    file_type = str(payload.get("file_type", "unknown"))

    seed = f"{job_id}:{upload_id}:{stored_path}:{file_type}"
    final_score = _stable_score(seed)
    risk_level = get_risk_level(final_score)
    confidence = round(max(final_score, 1 - final_score), 4)

    global_score = round(min(max(final_score + 0.03, 0.0), 1.0), 4)
    forensic_score = round(min(max(final_score - 0.04, 0.0), 1.0), 4)
    artifact_score = round(min(max(final_score + 0.08, 0.0), 1.0), 4)

    predictions = [
        {
            "model_name": "mock_global_deepfake_detector",
            "model_version": "mock-v1",
            "score": global_score,
            "label": risk_level,
            "confidence": confidence,
            "raw_output": {
                "engine": "mock",
                "file_type": file_type,
                "note": "This is a fake model prediction for development testing.",
            },
        },
        {
            "model_name": "mock_forensic_artifact_detector",
            "model_version": "mock-v1",
            "score": artifact_score,
            "label": risk_level,
            "confidence": confidence,
            "raw_output": {
                "engine": "mock",
                "checked_signals": [
                    "compression_artifacts",
                    "frequency_noise",
                    "edge_inconsistency",
                ],
            },
        },
    ]

    if file_type == "video":
        predictions.append(
            {
                "model_name": "mock_temporal_consistency_detector",
                "model_version": "mock-v1",
                "score": forensic_score,
                "label": risk_level,
                "confidence": confidence,
                "raw_output": {
                    "engine": "mock",
                    "checked_signals": [
                        "frame_consistency",
                        "motion_continuity",
                    ],
                },
            }
        )

    forensic_signals = [
        {
            "signal_name": "metadata_consistency",
            "signal_type": "metadata",
            "score": round(1 - final_score, 4),
            "severity": "low" if final_score < 0.55 else "medium",
            "description": "Mock metadata consistency check completed.",
            "raw_data": {
                "engine": "mock",
                "result": "metadata pattern checked",
            },
        },
        {
            "signal_name": "compression_artifacts",
            "signal_type": "forensic",
            "score": artifact_score,
            "severity": "low" if artifact_score < 0.45 else "medium",
            "description": "Mock compression artifact analysis completed.",
            "raw_data": {
                "engine": "mock",
                "result": "compression artifact score generated",
            },
        },
        {
            "signal_name": "frequency_artifacts",
            "signal_type": "frequency",
            "score": forensic_score,
            "severity": "low" if forensic_score < 0.45 else "medium",
            "description": "Mock frequency-domain artifact analysis completed.",
            "raw_data": {
                "engine": "mock",
                "result": "frequency signal score generated",
            },
        },
    ]

    return {
        "final_score": final_score,
        "confidence": confidence,
        "risk_level": risk_level,
        "summary": get_summary(final_score, risk_level),
        "predictions": predictions,
        "forensic_signals": forensic_signals,
        "metadata": {
            "engine": "mock-analysis-v1",
            "file_type": file_type,
            "stored_path": stored_path,
        },
    }
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import ai_settings
from app.detectors.face_crop_baseline_detector import (
    predict_face_crop_baseline,
)
from app.faces.face_cropper import crop_faces_from_image_bytes


def get_risk_level(score: float) -> str:
    if score < 0.33:
        return "likely_authentic"

    if score < 0.61:
        return "uncertain"

    if score < 0.80:
        return "suspicious"

    return "high_risk"


def get_prediction_label(score: float) -> str:
    if score >= 0.80:
        return "high_risk"

    if score >= 0.61:
        return "suspicious"

    if score >= 0.33:
        return "uncertain"

    return "likely_authentic"


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def build_temp_crop_dir() -> Path:
    run_id = (
        datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        + "_"
        + uuid.uuid4().hex[:8]
    )

    path = ai_settings.artifact_root / "pipeline_face_crops" / run_id
    path.mkdir(parents=True, exist_ok=True)

    return path


def enhance_image_result_with_face_crop_baseline(
    *,
    file_bytes: bytes,
    filename: str,
    mime_type: str,
    raw_result: dict[str, Any],
) -> dict[str, Any]:
    """
    Adds trained face-crop baseline evidence into the main image analysis result.

    If no baseline model has been trained yet, the main analysis still works.
    """

    enhanced_result = dict(raw_result)

    signals_summary = dict(enhanced_result.get("signals_summary") or {})
    model_versions = dict(enhanced_result.get("model_versions") or {})

    warnings: list[str] = list(signals_summary.get("warnings") or [])

    try:
        crop_output_dir = build_temp_crop_dir()

        crop_result = crop_faces_from_image_bytes(
            file_bytes=file_bytes,
            filename=filename,
            mime_type=mime_type,
            output_dir=crop_output_dir,
            relative_base=ai_settings.artifact_root,
            padding_ratio=0.25,
            min_quality_score=0.2,
            label=None,
            source_file_path=None,
        )

        crops = crop_result.get("crops") or []

        baseline_predictions: list[dict[str, Any]] = []

        for crop in crops:
            crop_path = Path(str(crop.get("crop_path") or ""))

            if not crop_path.exists():
                continue

            prediction = predict_face_crop_baseline(
                file_bytes=crop_path.read_bytes(),
                filename=crop_path.name,
                run_name=None,
            )
            baseline_predictions.append(
        {
        "face_id": crop.get("face_id"),
        "crop_path": str(crop_path),
        "quality_score": crop.get("quality_score"),

        "bbox": {
            "x": crop.get("x"),
            "y": crop.get("y"),
            "width": crop.get("width"),
            "height": crop.get("height"),
            "padded_x": crop.get("padded_x"),
            "padded_y": crop.get("padded_y"),
            "padded_width": crop.get("padded_width"),
            "padded_height": crop.get("padded_height"),
        },

        "fake_probability": prediction["fake_probability"],
        "real_probability": prediction["real_probability"],
        "confidence": prediction["confidence"],
        "predicted_label": prediction["predicted_label"],
        "model_name": prediction["model_name"],
        "model_version": prediction["model_version"],
        "run_name": prediction["run_name"],
        }
    )

        if not baseline_predictions:
            warnings.append(
                "Face-crop baseline was skipped because no usable face crop prediction was produced."
            )

            signals_summary["face_crop_baseline"] = {
                "enabled": True,
                "used": False,
                "reason": "no_usable_face_crop_prediction",
                "face_count": crop_result.get("face_count"),
                "saved_crop_count": crop_result.get("saved_crop_count"),
                "crop_warnings": crop_result.get("warnings") or [],
            }

            enhanced_result["signals_summary"] = signals_summary
            return enhanced_result

        baseline_fake_scores = [
            safe_float(item.get("fake_probability"))
            for item in baseline_predictions
        ]

        baseline_score = sum(baseline_fake_scores) / len(baseline_fake_scores)
        baseline_confidence = max(
            safe_float(item.get("confidence"))
            for item in baseline_predictions
        )

        heuristic_score = safe_float(enhanced_result.get("final_score"))

        combined_score = round(
            (heuristic_score * 0.65) + (baseline_score * 0.35),
            6,
        )

        combined_confidence = round(
            min(
                1.0,
                (
                    safe_float(enhanced_result.get("confidence"), 0.5) * 0.60
                    + baseline_confidence * 0.40
                ),
            ),
            6,
        )

        risk_level = get_risk_level(combined_score)

        enhanced_result["final_score"] = combined_score
        enhanced_result["risk_level"] = risk_level
        enhanced_result["confidence"] = combined_confidence
        enhanced_result["explanation"] = (
            f"{enhanced_result.get('explanation', 'Image analysis completed.')} "
            f"Face-crop baseline was also applied to {len(baseline_predictions)} crop(s)."
        )

        model_predictions = list(enhanced_result.get("model_predictions") or [])

        first_prediction = baseline_predictions[0]

        model_predictions.append(
            {
                "model_name": "face_crop_baseline_v1",
                "model_version": first_prediction.get("model_version")
                or "baseline-logistic-v1",
                "raw_score": baseline_score,
                "calibrated_score": baseline_score,
                "prediction_label": get_prediction_label(baseline_score),
                "target_region": "face_crop",
                "inference_time_ms": None,
            }
        )

        enhanced_result["model_predictions"] = model_predictions

        signals = list(signals_summary.get("signals") or [])

        signals.append(
            {
                "signal_type": "face_crop_baseline",
                "signal_name": "face_crop_baseline_fake_probability",
                "score": round(baseline_score, 6),
                "severity": (
                    "high"
                    if baseline_score >= 0.80
                    else "medium"
                    if baseline_score >= 0.50
                    else "low"
                ),
                "description": (
                    "Average fake probability from the trained face-crop baseline model."
                ),
                "raw_data": {
                    "baseline_predictions": baseline_predictions,
                    "heuristic_score_before_baseline": heuristic_score,
                    "combined_score_after_baseline": combined_score,
                    "weighting": {
                        "heuristic": 0.65,
                        "face_crop_baseline": 0.35,
                    },
                },
            }
        )

        signals_summary["signals"] = signals

        signals_summary["face_crop_baseline"] = {
            "enabled": True,
            "used": True,
            "baseline_score": round(baseline_score, 6),
            "baseline_confidence": baseline_confidence,
            "prediction_count": len(baseline_predictions),
            "predictions": baseline_predictions,
        }

        signals_summary["face_evidence"] = [
    {
        "face_id": item.get("face_id"),
        "bbox": item.get("bbox"),
        "face_score": item.get("fake_probability"),
        "detection_confidence": item.get("confidence"),
        "crop_path": item.get("crop_path"),
        "quality_score": item.get("quality_score"),
        "model_name": item.get("model_name"),
        "model_version": item.get("model_version"),
        "predicted_label": item.get("predicted_label"),
        "details": item,
    }
    for item in baseline_predictions
]

        signals_summary["warnings"] = warnings

        existing_models = list(model_versions.get("models") or [])

        existing_models.append(
            {
                "model_name": "face_crop_baseline_v1",
                "model_version": first_prediction.get("model_version")
                or "baseline-logistic-v1",
            }
        )

        model_versions["models"] = existing_models
        model_versions["face_crop_baseline"] = {
            "run_name": first_prediction.get("run_name"),
            "model_version": first_prediction.get("model_version"),
        }

        enhanced_result["signals_summary"] = signals_summary
        enhanced_result["model_versions"] = model_versions

        return enhanced_result

    except FileNotFoundError:
        warnings.append(
            "Face-crop baseline was skipped because no trained baseline model was found."
        )

        signals_summary["warnings"] = warnings
        signals_summary["face_crop_baseline"] = {
            "enabled": False,
            "used": False,
            "reason": "no_trained_model_found",
        }

        enhanced_result["signals_summary"] = signals_summary

        return enhanced_result

    except Exception as exc:
        warnings.append(f"Face-crop baseline failed and was skipped: {exc}")

        signals_summary["warnings"] = warnings
        signals_summary["face_crop_baseline"] = {
            "enabled": True,
            "used": False,
            "reason": str(exc),
        }

        enhanced_result["signals_summary"] = signals_summary

        return enhanced_result
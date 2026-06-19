from __future__ import annotations

import time
from io import BytesIO
from typing import Any

import numpy as np
from PIL import Image, ImageFilter


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def round_score(value: float) -> float:
    return round(clamp(value), 4)


def get_risk_level(score: float) -> str:
    if score < 0.33:
        return "likely_authentic"

    if score < 0.61:
        return "uncertain"

    if score < 0.8:
        return "suspicious"

    return "high_risk"


def get_explanation(risk_level: str, final_score: float) -> str:
    percentage = round(final_score * 100)

    if risk_level == "likely_authentic":
        return (
            f"The foundation image analyzer found low-risk visual quality signals "
            f"with an estimated score of {percentage}%. This is not a final trained "
            f"deepfake model result yet."
        )

    if risk_level == "uncertain":
        return (
            f"The foundation image analyzer found mixed visual signals with an "
            f"estimated score of {percentage}%. A trained deepfake model should review it."
        )

    if risk_level == "suspicious":
        return (
            f"The foundation image analyzer found suspicious visual quality patterns "
            f"with an estimated score of {percentage}%. Further AI analysis is recommended."
        )

    return (
        f"The foundation image analyzer found high-risk visual quality patterns "
        f"with an estimated score of {percentage}%. Human review and trained model "
        f"verification are recommended."
    )


def severity_from_score(score: float) -> str:
    if score < 0.33:
        return "low"

    if score < 0.66:
        return "medium"

    return "high"


def analyze_image_bytes(
    *,
    file_bytes: bytes,
    filename: str,
    mime_type: str,
) -> dict[str, Any]:
    started_at = time.perf_counter()

    image = Image.open(BytesIO(file_bytes))
    image.load()

    width, height = image.size
    mode = image.mode

    exif_data = image.getexif()
    has_exif = bool(exif_data)

    rgb_image = image.convert("RGB")
    gray_image = image.convert("L")

    rgb_array = np.asarray(rgb_image).astype(np.float32)
    gray_array = np.asarray(gray_image).astype(np.float32)

    brightness = float(gray_array.mean() / 255.0)
    contrast = float(gray_array.std() / 128.0)

    gradient_y, gradient_x = np.gradient(gray_array)
    edge_energy = np.sqrt((gradient_x ** 2) + (gradient_y ** 2))
    sharpness = float(edge_energy.mean() / 50.0)

    blurred = gray_image.filter(ImageFilter.GaussianBlur(radius=1.2))
    blurred_array = np.asarray(blurred).astype(np.float32)
    residual = np.abs(gray_array - blurred_array)
    noise_estimate = float(residual.mean() / 255.0)

    channel_means = rgb_array.mean(axis=(0, 1)) / 255.0
    color_imbalance = float(np.std(channel_means) * 2.0)

    metadata_risk = 0.12 if has_exif else 0.35
    sharpness_risk = clamp((0.35 - sharpness) / 0.35)
    noise_risk = clamp(noise_estimate / 0.12)
    contrast_risk = clamp(abs(contrast - 0.45) / 0.45)
    color_risk = clamp(color_imbalance)

    final_score = round_score(
        (metadata_risk * 0.15)
        + (sharpness_risk * 0.25)
        + (noise_risk * 0.25)
        + (contrast_risk * 0.2)
        + (color_risk * 0.15)
    )

    confidence = round_score(1.0 - min(abs(final_score - 0.5), 0.5))

    risk_level = get_risk_level(final_score)

    forensic_signals = [
        {
            "signal_type": "metadata",
            "signal_name": "metadata_presence",
            "score": round_score(metadata_risk),
            "severity": severity_from_score(metadata_risk),
            "description": (
                "EXIF metadata was found."
                if has_exif
                else "No EXIF metadata was found. This can happen after editing, compression, or social media sharing."
            ),
            "raw_data": {
                "has_exif": has_exif,
                "exif_key_count": len(exif_data) if has_exif else 0,
            },
        },
        {
            "signal_type": "sharpness",
            "signal_name": "edge_sharpness",
            "score": round_score(sharpness_risk),
            "severity": severity_from_score(sharpness_risk),
            "description": "Estimated image sharpness using pixel edge gradients.",
            "raw_data": {
                "sharpness": round_score(sharpness),
            },
        },
        {
            "signal_type": "noise",
            "signal_name": "high_frequency_noise",
            "score": round_score(noise_risk),
            "severity": severity_from_score(noise_risk),
            "description": "Estimated high-frequency residual noise from the image.",
            "raw_data": {
                "noise_estimate": round_score(noise_estimate),
            },
        },
        {
            "signal_type": "contrast",
            "signal_name": "contrast_distribution",
            "score": round_score(contrast_risk),
            "severity": severity_from_score(contrast_risk),
            "description": "Estimated abnormal contrast distribution risk.",
            "raw_data": {
                "brightness": round_score(brightness),
                "contrast": round_score(contrast),
            },
        },
        {
            "signal_type": "color",
            "signal_name": "channel_imbalance",
            "score": round_score(color_risk),
            "severity": severity_from_score(color_risk),
            "description": "Estimated RGB channel imbalance.",
            "raw_data": {
                "red_mean": round_score(float(channel_means[0])),
                "green_mean": round_score(float(channel_means[1])),
                "blue_mean": round_score(float(channel_means[2])),
            },
        },
    ]

    model_predictions = [
        {
            "model_name": "foundation_image_forensic_analyzer",
            "model_version": "foundation-v1",
            "raw_score": final_score,
            "calibrated_score": final_score,
            "prediction_label": risk_level,
            "target_region": "global",
            "inference_time_ms": int((time.perf_counter() - started_at) * 1000),
        }
    ]

    processing_time_ms = int((time.perf_counter() - started_at) * 1000)

    return {
        "engine": "ai-service-foundation-v1",
        "media_type": "image",
        "filename": filename,
        "mime_type": mime_type,
        "image": {
            "width": width,
            "height": height,
            "mode": mode,
        },
        "final_score": final_score,
        "risk_level": risk_level,
        "confidence": confidence,
        "explanation": get_explanation(risk_level, final_score),
        "processing_time_ms": processing_time_ms,
        "model_predictions": model_predictions,
        "forensic_signals": forensic_signals,
        "model_versions": {
            "engine": "ai-service-foundation-v1",
            "models": [
                {
                    "model_name": "foundation_image_forensic_analyzer",
                    "model_version": "foundation-v1",
                }
            ],
        },
        "signals_summary": {
            "summary": (
                "Foundation image forensic analysis completed. "
                "This is a real pixel-based service foundation, but not a trained deepfake model yet."
            ),
            "prediction_count": len(model_predictions),
            "forensic_signal_count": len(forensic_signals),
            "signals": forensic_signals,
        },
    }
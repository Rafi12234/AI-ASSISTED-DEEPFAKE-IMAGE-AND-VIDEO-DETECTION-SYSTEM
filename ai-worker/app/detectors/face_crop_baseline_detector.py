from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from app.config import ai_settings
from app.training.face_crop_baseline import (
    extract_image_features,
    get_latest_face_crop_baseline_run,
    get_model_root,
)


def predict_face_crop_baseline(
    *,
    file_bytes: bytes,
    filename: str,
    run_name: str | None = None,
) -> dict[str, Any]:
    if not file_bytes:
        raise ValueError("Uploaded image is empty.")

    if run_name:
        metadata_path = get_model_root() / run_name / "metadata.json"

        if not metadata_path.exists():
            raise FileNotFoundError(f"Model run not found: {run_name}")

        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    else:
        metadata = get_latest_face_crop_baseline_run()

    model_path = Path(metadata["model_path"])
    scaler_path = Path(metadata["scaler_path"])

    if not model_path.exists():
        raise FileNotFoundError(f"Model file missing: {model_path}")

    if not scaler_path.exists():
        raise FileNotFoundError(f"Scaler file missing: {scaler_path}")

    temp_dir = ai_settings.artifact_root / "tmp_predictions"
    temp_dir.mkdir(parents=True, exist_ok=True)

    temp_path = temp_dir / filename
    temp_path.write_bytes(file_bytes)

    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)

    image_size = int(metadata.get("image_size") or 128)
    features = extract_image_features(temp_path, image_size)

    x_data = np.asarray([features], dtype=np.float32)
    x_scaled = scaler.transform(x_data)

    probabilities = model.predict_proba(x_scaled)[0]
    real_probability = float(probabilities[0])
    fake_probability = float(probabilities[1])

    predicted_label = "fake" if fake_probability >= 0.5 else "real"
    confidence = max(real_probability, fake_probability)

    return {
        "filename": filename,
        "model_name": metadata.get("model_name"),
        "model_version": metadata.get("model_version"),
        "run_name": metadata.get("run_name"),
        "predicted_label": predicted_label,
        "fake_probability": round(fake_probability, 6),
        "real_probability": round(real_probability, 6),
        "confidence": round(confidence, 6),
        "features_used": len(features),
        "important_warning": (
            "This baseline prediction is for pipeline testing only. "
            "Do not treat it as a reliable production deepfake verdict."
        ),
    }